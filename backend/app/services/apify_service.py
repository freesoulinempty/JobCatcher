"""
Apify LinkedIn爬虫服务 / Apify LinkedIn scraping service
"""

import asyncio
from typing import List, Dict, Any, Optional
from apify_client import ApifyClientAsync
from ..core.config import settings
from ..models.job import JobPosting, JobSource
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ApifyLinkedInService:
    """Apify LinkedIn爬虫服务类 / Apify LinkedIn scraping service class"""
    
    def __init__(self):
        self.client = ApifyClientAsync(settings.apify_api_token)
        self.actor_id = settings.apify_linkedin_actor_id
        
    async def search_jobs(
        self, 
        job_title: str, 
        location: Optional[str] = None, 
        limit: int = 25
    ) -> List[JobPosting]:
        """
        搜索LinkedIn职位 / Search LinkedIn jobs
        
        Args:
            job_title: 职位标题 / Job title
            location: 工作地点 / Work location  
            limit: 结果数量限制 / Result limit
            
        Returns:
            职位列表 / List of job postings
        """
        try:
            # 构建搜索参数 / Build search parameters
            # 严格按照用户提供的标准格式 / Strictly follow user's standard format
            run_input = {
                "limit": limit,  # 按图片格式：limit而不是maxResults
                "location": location or "Germany",
                "datePosted": "r604800",  # 限制为7天内发布的职位 / Limit to jobs posted within 7 days (closest to 14 days requirement)
                "proxy": {
                    "useApifyProxy": True,
                    "apifyProxyGroups": ["RESIDENTIAL"]
                },
                "title": job_title  # 按图片格式：title而不是keywords
            }
            
            logger.info(f"Starting LinkedIn job search: {job_title} in {location or 'Germany'}, limit: {limit}")
            
            # 执行爬虫 / Run the scraper
            run = await self.client.actor(self.actor_id).call(run_input=run_input)
            
            # 获取结果 / Get results
            results = []
            async for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
                try:
                    job_posting = self._parse_linkedin_job(item)
                    if job_posting:
                        results.append(job_posting)
                except Exception as e:
                    logger.error(f"Error parsing job item: {e}")
                    continue
                    
            logger.info(f"Successfully scraped {len(results)} jobs from LinkedIn")
            return results
            
        except Exception as e:
            logger.error(f"LinkedIn scraping failed: {e}")
            return []
    
    async def scheduled_crawl(self) -> List[JobPosting]:
        """
        定时爬取预设职位 / Scheduled crawling for preset job titles
        根据README要求更新预设岗位列表 / Update preset job list according to README requirements
        
        Returns:
            所有爬取的职位列表 / List of all scraped jobs
        """
        # 根据README更新：8个预设岗位 / According to README update: 8 preset job titles
        preset_jobs = ["engineer", "manager", "IT", "Finance", "Sales", "Nurse", "Consultant", "software developer"]
        all_jobs = []
        
        for job_title in preset_jobs:
            try:
                jobs = await self.search_jobs(job_title, location=None, limit=25)
                all_jobs.extend(jobs)
                
                # 添加延迟避免频率限制 / Add delay to avoid rate limiting
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Failed to crawl jobs for {job_title}: {e}")
                continue
                
        logger.info(f"Scheduled crawl completed: {len(all_jobs)} total jobs from {len(preset_jobs)} job categories")
        return all_jobs
    
    def _parse_linkedin_job(self, item: Dict[str, Any]) -> Optional[JobPosting]:
        """
        解析LinkedIn职位数据 / Parse LinkedIn job data
        根据用户提供的标准输出格式 / Based on user's standard output format
        
        Args:
            item: 原始职位数据 / Raw job data
            
        Returns:
            职位对象或None / JobPosting object or None
        """
        try:
            # 检查必需字段 / Check required fields
            if not all(key in item for key in ["id", "title", "companyName", "url"]):
                return None
                
            # 解析发布时间 / Parse posted date
            posted_date = None
            if item.get("postedDate"):
                try:
                    posted_date = datetime.fromisoformat(
                        item["postedDate"].replace("Z", "+00:00")
                    )
                except:
                    posted_date = None
            
            # 根据README示例，workType是行业类型，contractType是工作方式 / According to README, workType is industry type, contractType is work mode
            # 将contractType映射到work_type字段 / Map contractType to work_type field
            work_type = None
            raw_contract_type = item.get("contractType")
            if raw_contract_type:
                # 处理LinkedIn返回的contractType值 / Handle LinkedIn contractType values
                contract_mapping = {
                    "Full-time": "Full-time",
                    "Part-time": "Part-time", 
                    "Contract": "Contract",
                    "Internship": "Internship"
                }
                work_type = contract_mapping.get(raw_contract_type)
            
            # 如果workType包含工作方式信息，也尝试提取 / If workType contains work mode info, try to extract
            raw_work_type = item.get("workType")
            if not work_type and raw_work_type:
                if raw_work_type in ["Remote", "Hybrid", "On-site"]:
                    work_type = raw_work_type
            
            # experienceLevel字段映射 / experienceLevel field mapping  
            experience_level = None
            raw_experience = item.get("experienceLevel")
            if raw_experience:
                experience_mapping = {
                    "Entry level": "Entry level",
                    "Mid-Senior level": "Mid-Senior level", 
                    "Senior level": "Senior level",
                    "Executive": "Executive",
                    "Internship": "Internship"
                }
                experience_level = experience_mapping.get(raw_experience)
            
            # 创建职位对象 / Create job posting object
            job_posting = JobPosting(
                id=f"linkedin_{item['id']}",
                title=item["title"],
                company_name=item["companyName"],
                company_url=item.get("companyUrl"),
                location=item.get("location", ""),
                work_type=work_type,
                contract_type=item.get("contractType"),
                experience_level=experience_level,
                sector=item.get("sector"),
                salary=item.get("salary", ""),
                description=item.get("description", ""),
                url=item["url"],
                apply_url=item.get("applyUrl"),
                posted_date=posted_date,
                posted_time_ago=item.get("postedTimeAgo"),
                applications_count=item.get("applicationsCount"),
                source=JobSource.LINKEDIN
            )
            
            return job_posting
            
        except Exception as e:
            logger.error(f"Error parsing LinkedIn job: {e}")
            return None
    
    async def test_connection(self) -> bool:
        """
        测试Apify连接 / Test Apify connection
        
        Returns:
            连接状态 / Connection status
        """
        try:
            # 执行一个小的测试请求 / Execute a small test request
            run_input = {
                "title": "test",  # 按图片格式：title
                "location": "Germany", 
                "limit": 1,  # 按图片格式：limit
                "proxy": {
                    "useApifyProxy": True,
                    "apifyProxyGroups": ["RESIDENTIAL"]
                }
            }
            
            run = await self.client.actor(self.actor_id).call(run_input=run_input)
            return run is not None
            
        except Exception as e:
            logger.error(f"Apify connection test failed: {e}")
            return False 