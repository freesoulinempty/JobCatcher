"""
定时任务调度服务 / Scheduled task service
"""

import asyncio
import logging
import aiohttp
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from typing import List, Dict, Any
import pytz

from ..services.apify_service import ApifyLinkedInService
from ..services.zyte_service import ZyteIndeedService
from ..database.connection import get_chroma_client, get_openai_embedding_client, get_text_embedding
from ..models.job import JobPosting

logger = logging.getLogger(__name__)


class SchedulerService:
    """定时任务服务类 / Scheduler service class"""
    
    def __init__(self):
        # 设置德国时区 / Set German timezone
        self.german_tz = pytz.timezone('Europe/Berlin')
        self.scheduler = AsyncIOScheduler(timezone=self.german_tz)
        self.apify_service = ApifyLinkedInService()
        self.zyte_service = ZyteIndeedService()
        self.chroma_client = get_chroma_client()
        
    async def start(self):
        """启动定时任务 / Start scheduled tasks"""
        try:
            # 添加定时任务 / Add scheduled tasks
            try:
                # 定时爬取任务：德国时间晚上8.00点 / Scheduled crawling task: 20.00 PM German time
                self.scheduler.add_job(
                    self._scheduled_crawl_job,
                    CronTrigger(hour=20, minute=0, timezone=self.german_tz),  # 德国时间晚上8.00点 / 20.00 PM German time
                    id="daily_crawl",
                    name="Daily Job Crawling",
                    replace_existing=True
                )
                logger.info("✅ 定时爬取任务已设置：德国时间每天晚上8.00点 / Scheduled crawling task set: 20.00 PM German time daily")
                
                # 数据清理任务：德国时间下午9.00点 / Data cleanup task: 9.00 PM German time
                self.scheduler.add_job(
                    self._scheduled_cleanup_job,
                    CronTrigger(hour=21, minute=0, timezone=self.german_tz),  # 德国时间下午9.00点 /  9.00 PM German time
                    id="daily_cleanup",
                    name="Daily Data Cleanup",
                    replace_existing=True
                )
                logger.info("✅ 数据清理任务已设置：德国时间每天下午9.00点 / Data cleanup task set: 9.00 PM German time daily")
            except Exception as e:
                logger.error(f"Failed to add scheduled tasks: {e}")
            
            self.scheduler.start()
            
            # 记录当前德国时间 / Log current German time
            current_german_time = datetime.now(self.german_tz)
            logger.info(f"Scheduler service started successfully")
            logger.info(f"Current German time: {current_german_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            logger.info(f"Next crawl scheduled for: German time 20:00 daily")
            logger.info(f"Next cleanup scheduled for: German time 21:00 daily")
            
        except Exception as e:
            logger.error(f"Failed to start scheduler service: {e}")
            raise
    
    async def stop(self):
        """停止定时任务 / Stop scheduled tasks"""
        try:
            self.scheduler.shutdown()
            logger.info("Scheduler service stopped")
        except Exception as e:
            logger.error(f"Failed to stop scheduler service: {e}")
    
    async def _scheduled_crawl_job(self):
        """
        定时爬取任务 / Scheduled crawling job
        按照README要求：每日20.00点定时爬取预设岗位数据 / According to README: daily crawling at 20.00 for preset job titles
        LinkedIn预设岗位: "engineer","manager","IT","Finance","Sales","Nurse","Consultant","software developer"
        Indeed预设岗位: "Web","cloud","AI","Data","software"
        """
        try:
            logger.info("Starting scheduled crawling job...")
            
            # 并行执行LinkedIn和Indeed爬取 / Execute LinkedIn and Indeed crawling in parallel
            linkedin_jobs, indeed_jobs = await asyncio.gather(
                self.apify_service.scheduled_crawl(),
                self.zyte_service.scheduled_crawl(),
                return_exceptions=True
            )
            
            # 处理异常结果 / Handle exception results
            if isinstance(linkedin_jobs, Exception):
                logger.error(f"LinkedIn scheduled crawl failed: {linkedin_jobs}")
                linkedin_jobs = []
            if isinstance(indeed_jobs, Exception):
                logger.error(f"Indeed scheduled crawl failed: {indeed_jobs}")
                indeed_jobs = []
            
            # 合并所有职位 / Merge all jobs
            all_jobs = linkedin_jobs + indeed_jobs
            
            # 存储到向量数据库 / Store to vector database
            if all_jobs:
                await self._store_crawled_jobs(all_jobs)
                
            logger.info(f"Scheduled crawling completed: {len(all_jobs)} jobs processed")
            
        except Exception as e:
            logger.error(f"Scheduled crawling job failed: {e}")
    
    async def _scheduled_cleanup_job(self):
        """
        定时数据清理任务 / Scheduled data cleanup job
        按照README要求：每天下午9.00点访问Chroma中所有岗位URL，如果URL失效则清理
        清理14天之前的岗位数据，防止僵尸岗位
        """
        try:
            logger.info("Starting scheduled cleanup job...")
            
            # 获取jobs集合 / Get jobs collection
            try:
                jobs_collection = self.chroma_client.get_collection("jobs")
            except:
                logger.warning("Jobs collection not found, skipping cleanup")
                return
            
            # 获取所有职位数据 / Get all job data
            all_jobs_data = jobs_collection.get()
            
            if not all_jobs_data.get('ids'):
                logger.info("No jobs found for cleanup")
                return
            
            # 清理统计 / Cleanup statistics
            cleanup_count = 0
            total_jobs = len(all_jobs_data['ids'])
            cleanup_reasons = {
                'age_expired': 0,
                'invalid_url': 0,
                'url_404': 0,
                'empty_url': 0
            }
            
            logger.info(f"Starting cleanup check for {total_jobs} jobs...")
            
            for i, job_id in enumerate(all_jobs_data['ids']):
                try:
                    metadata = all_jobs_data['metadatas'][i] if all_jobs_data.get('metadatas') else {}
                    job_url = metadata.get('url', '')
                    created_at = metadata.get('created_at', '')
                    job_title = metadata.get('title', 'Unknown')
                    
                    # 检查是否需要清理 / Check if cleanup is needed
                    should_cleanup, reason = await self._should_cleanup_job_with_reason(job_url, created_at)
                    
                    if should_cleanup:
                        # 删除职位 / Delete job
                        jobs_collection.delete(ids=[job_id])
                        cleanup_count += 1
                        cleanup_reasons[reason] += 1
                        logger.info(f"Cleaned up job ({reason}): {job_title[:50]} - {job_url[:100]}")
                    
                    # 进度报告 / Progress report
                    if (i + 1) % 50 == 0:
                        logger.info(f"Progress: {i + 1}/{total_jobs} jobs checked, {cleanup_count} cleaned")
                    
                    # 添加延迟避免过度请求 / Add delay to avoid excessive requests
                    if i % 10 == 0:
                        await asyncio.sleep(1)
                        
                except Exception as e:
                    logger.error(f"Error processing job {job_id} for cleanup: {e}")
                    continue
            
            # 详细的清理报告 / Detailed cleanup report
            logger.info(f"Cleanup completed: {cleanup_count}/{total_jobs} jobs cleaned up")
            logger.info(f"Cleanup reasons: Age expired: {cleanup_reasons['age_expired']}, "
                       f"Invalid URL: {cleanup_reasons['invalid_url']}, "
                       f"URL 404: {cleanup_reasons['url_404']}, "
                       f"Empty URL: {cleanup_reasons['empty_url']}")
            logger.info(f"Remaining jobs: {total_jobs - cleanup_count}")
            
        except Exception as e:
            logger.error(f"Scheduled cleanup job failed: {e}")
    
    async def _store_crawled_jobs(self, jobs: List[JobPosting]):
        """
        存储爬取的职位到向量数据库 / Store crawled jobs to vector database
        使用OpenAI text-embedding-3-small进行向量化，使用英德语进行向量化 / Use OpenAI text-embedding-3-small for vectorization with English/German
        
        Args:
            jobs: 职位列表 / List of jobs
        """
        try:
            # 获取数据库连接 / Get database connections
            chroma_client = get_chroma_client()
            openai_client = get_openai_embedding_client()
            
            # 获取或创建jobs集合 / Get or create jobs collection
            try:
                jobs_collection = chroma_client.get_collection("jobs")
            except:
                jobs_collection = chroma_client.create_collection(
                    name="jobs",
                    metadata={"description": "Job postings vector store with OpenAI embeddings"}
                )
            
            stored_count = 0
            skipped_count = 0
            
            for job in jobs:
                try:
                    # 检查是否已存在（去重机制）/ Check if already exists (deduplication)
                    existing = jobs_collection.get(ids=[job.id])
                    if existing['ids']:
                        skipped_count += 1
                        continue
                    
                    # 构建用于向量化的文档内容（英德语）/ Build document content for vectorization (English/German)
                    document = f"Job: {job.title} Company: {job.company_name} Location: {job.location} Description: {job.description[:500]}"
                    
                    # 使用OpenAI text-embedding-3-small模型进行向量化 / Use OpenAI text-embedding-3-small for vectorization
                    logger.debug(f"Vectorizing job with OpenAI: {job.title} at {job.company_name}")
                    try:
                        embedding = get_text_embedding(openai_client, document)
                        logger.debug(f"✅ Successfully generated embedding (dimension: {len(embedding)})")
                    except Exception as e:
                        logger.error(f"❌ Failed to generate embedding for job {job.id}: {e}")
                        continue
                    
                    # 确保所有metadata字段都不包含None值 / Ensure no None values in metadata
                    metadata = {
                        "id": job.id,
                        "title": job.title or "",
                        "company_name": job.company_name or "",
                        "location": job.location or "",
                        "work_type": job.work_type.value if job.work_type else "",
                        "contract_type": job.contract_type or "",
                        "experience_level": job.experience_level.value if job.experience_level else "",
                        "sector": job.sector or "",
                        "salary": job.salary or "",
                        "source": job.source.value if job.source else "",
                        "url": str(job.url) if job.url else "",
                        "apply_url": str(job.apply_url) if job.apply_url else "",
                        "posted_time_ago": job.posted_time_ago or "",
                        "applications_count": str(job.applications_count) if job.applications_count else "0",
                        "description_preview": (job.description[:200] if job.description else ""),
                        "full_description": job.description or "",
                        "embedding_model": "text-embedding-3-small",
                        "created_at": datetime.now().isoformat()
                    }
                    
                    jobs_collection.add(
                        documents=[document],
                        embeddings=[embedding],
                        metadatas=[metadata],
                        ids=[job.id]
                    )
                    stored_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to store job {job.id}: {e}")
                    continue
            
            logger.info(f"Vector DB storage: {stored_count} new jobs vectorized with OpenAI text-embedding-3-small and stored, {skipped_count} duplicates skipped")
            return stored_count
            
        except Exception as e:
            logger.error(f"Failed to store jobs in vector DB: {e}")
            return 0
    
    async def _should_cleanup_job_with_reason(self, job_url: str, created_at: str) -> tuple[bool, str]:
        """
        检查职位是否需要清理并返回原因 / Check if job should be cleaned up and return reason
        
        Args:
            job_url: 职位URL / Job URL
            created_at: 创建时间 / Creation time
            
        Returns:
            (是否需要清理, 原因) / (Whether cleanup is needed, reason)
        """
        try:
            # 检查是否超过14天 / Check if older than 14 days
            if created_at:
                try:
                    job_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    age_days = (datetime.now() - job_date).days
                    if age_days > 14:
                        return True, 'age_expired'
                except Exception as e:
                    logger.warning(f"Failed to parse job date {created_at}: {e}, keeping job")
                    return False, 'date_parse_error'
            
            # 检查URL是否有效 / Check if URL is valid
            if not job_url or job_url.strip() == "":
                return True, 'empty_url'
            
            if not (job_url.startswith('http://') or job_url.startswith('https://')):
                return True, 'invalid_url'
            
            # 网络检查 - 只检查404
            try:
                async with aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=15),
                    connector=aiohttp.TCPConnector(limit=10, limit_per_host=3)
                ) as session:
                    async with session.get(job_url, allow_redirects=True) as response:
                        if response.status == 404:
                            return True, 'url_404'
                        else:
                            return False, 'url_accessible'
            except Exception:
                # 网络错误时保守起见不删除
                return False, 'network_error'
            
        except Exception as e:
            logger.error(f"Error checking job cleanup status: {e}")
            return False, 'check_error'
    