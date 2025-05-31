"""
Zyte API Indeed爬虫服务 / Zyte API Indeed scraping service
"""

import asyncio
from typing import List, Dict, Any, Optional
from zyte_api import AsyncZyteAPI
from ..core.config import settings
from ..models.job import JobPosting, JobSource
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ZyteIndeedService:
    """Zyte API Indeed爬虫服务类 / Zyte API Indeed scraping service class"""
    
    def __init__(self):
        self.client = AsyncZyteAPI(api_key=settings.zyte_api_key)
        
    async def search_jobs(
        self, 
        job_title: str, 
        location: Optional[str] = None, 
        limit: int = 25
    ) -> List[JobPosting]:
        """
        搜索Indeed职位 / Search Indeed jobs
        
        Args:
            job_title: 职位标题 / Job title
            location: 工作地点 / Work location  
            limit: 结果数量限制 / Result limit
            
        Returns:
            职位列表 / List of job postings
        """
        try:
            # 构建Indeed URL / Build Indeed URL
            base_url = "https://de.indeed.com/jobs"
            params = f"?q={job_title.replace(' ', '+')}"
            
            if location:
                params += f"&l={location.replace(' ', '+')}"
            else:
                params += "&l="  # 空地点，按README要求
                
            url = base_url + params
            
            logger.info(f"Starting Indeed job search: {job_title} in {location or 'Germany'}")
            
            # 先爬取岗位列表 / First scrape job list
            job_links = await self._scrape_job_navigation(url)
            
            # 限制结果数量 / Limit results
            job_links = job_links[:limit]
            
            # 爬取岗位详情 / Scrape job details
            jobs = []
            for job_url in job_links:
                try:
                    job_posting = await self._scrape_job_details(job_url)
                    if job_posting:
                        jobs.append(job_posting)
                        
                    # 添加延迟避免频率限制 / Add delay to avoid rate limiting
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error scraping job details from {job_url}: {e}")
                    continue
                    
            logger.info(f"Successfully scraped {len(jobs)} jobs from Indeed")
            return jobs
            
        except Exception as e:
            logger.error(f"Indeed scraping failed: {e}")
            return []
    
    async def scheduled_crawl(self) -> List[JobPosting]:
        """
        定时爬取预设职位 / Scheduled crawling for preset job titles
        
        Returns:
            所有爬取的职位列表 / List of all scraped jobs
        """
        # README要求的预设岗位名称 / Preset job titles as required by README
        preset_jobs = ["Web", "cloud", "AI", "Data", "software"]
        all_jobs = []
        
        for job_title in preset_jobs:
            try:
                jobs = await self.search_jobs(job_title, location=None, limit=25)
                all_jobs.extend(jobs)
                
                # 添加延迟避免频率限制 / Add delay to avoid rate limiting
                await asyncio.sleep(3)
                
            except Exception as e:
                logger.error(f"Failed to crawl jobs for {job_title}: {e}")
                continue
                
        logger.info(f"Scheduled crawl completed: {len(all_jobs)} total jobs")
        return all_jobs
    
    async def _scrape_job_navigation(self, url: str) -> List[str]:
        """
        爬取岗位列表 / Scrape job list
        
        Args:
            url: Indeed搜索URL / Indeed search URL
            
        Returns:
            职位详情链接列表 / List of job detail URLs
        """
        try:
            # 按照README示例调用方式 / Call according to README example
            api_response = await self.client.get({
                "url": url,
                "jobPostingNavigation": True,
                "jobPostingNavigationOptions": {"extractFrom": "httpResponseBody"},
            })
            
            job_navigation = api_response.get("jobPostingNavigation", {})
            job_links = []
            
            # 提取职位链接 / Extract job links - 修复字段名从"jobs"改为"items"
            if "items" in job_navigation:
                for job in job_navigation["items"]:
                    if "url" in job:
                        job_links.append(job["url"])
            
            logger.info(f"Found {len(job_links)} job links from navigation")
            return job_links
            
        except Exception as e:
            logger.error(f"Failed to scrape job navigation: {e}")
            return []
    
    async def _scrape_job_details(self, job_url: str) -> Optional[JobPosting]:
        """
        爬取岗位详情 / Scrape job details
        
        Args:
            job_url: 职位详情URL / Job detail URL
            
        Returns:
            职位对象或None / JobPosting object or None
        """
        try:
            # 按照README示例调用方式 / Call according to README example
            api_response = await self.client.get({
                "url": job_url,
                "jobPosting": True,
                "jobPostingOptions": {"extractFrom": "httpResponseBody"},
            })
            
            job_posting_data = api_response.get("jobPosting")
            if not job_posting_data:
                return None
                
            # 解析职位数据 / Parse job data
            job_posting = self._parse_indeed_job(job_posting_data, job_url)
            return job_posting
            
        except Exception as e:
            logger.error(f"Failed to scrape job details from {job_url}: {e}")
            return None
    
    def _parse_indeed_job(self, job_data: Dict[str, Any], job_url: str) -> Optional[JobPosting]:
        """
        解析Indeed职位数据 / Parse Indeed job data
        
        Args:
            job_data: 原始职位数据 / Raw job data
            job_url: 职位URL / Job URL
            
        Returns:
            职位对象或None / JobPosting object or None
        """
        try:
            # 根据Zyte API实际返回结构提取基本信息 / Extract basic information based on actual Zyte API response structure
            title = job_data.get("jobTitle", "")  # 修复：从"name"改为"jobTitle"
            company_name = ""
            location = ""
            description = job_data.get("description", "")
            work_type = "Full-time"  # 默认值 / Default value
            
            # 提取公司信息 / Extract company information
            if "hiringOrganization" in job_data:
                company_info = job_data["hiringOrganization"]
                if isinstance(company_info, dict):
                    company_name = company_info.get("name", "")
                elif isinstance(company_info, str):
                    company_name = company_info
            
            # 提取地点信息 / Extract location information - 修复解析逻辑
            if "jobLocation" in job_data:
                location_info = job_data["jobLocation"]
                if isinstance(location_info, dict):
                    # 优先使用raw字段 / Prefer raw field
                    if "raw" in location_info:
                        location = location_info["raw"]
                    elif "address" in location_info:
                        address = location_info["address"]
                        if isinstance(address, dict):
                            location = address.get("addressLocality", "")
                        elif isinstance(address, str):
                            location = address
                elif isinstance(location_info, str):
                    location = location_info
            
            # 提取工作类型 / Extract employment type
            if "employmentType" in job_data:
                employment_type = job_data["employmentType"]
                if employment_type == "FULL_TIME":
                    work_type = "Full-time"
                elif employment_type == "PART_TIME":
                    work_type = "Part-time"
                elif employment_type == "CONTRACT":
                    work_type = "Contract"
                elif employment_type == "TEMPORARY":
                    work_type = "Temporary"
                else:
                    work_type = "Full-time"  # 默认值 / Default value
            
            # 检查必需字段 / Check required fields
            if not title or not company_name:
                logger.warning(f"Missing required fields - title: {title}, company: {company_name}")
                return None
                
            # 生成唯一ID / Generate unique ID
            job_id = f"indeed_{hash(job_url)}"
            
            # 创建职位对象 / Create job posting object
            job_posting = JobPosting(
                id=job_id,
                title=title,
                company_name=company_name,
                location=location or "Germany",
                description=description,
                url=job_url,
                source=JobSource.INDEED,
                posted_date=datetime.now(),
                work_type=work_type
            )
            
            return job_posting
            
        except Exception as e:
            logger.error(f"Error parsing Indeed job: {e}")
            return None
    
    async def test_connection(self) -> bool:
        """
        测试Zyte API连接 / Test Zyte API connection
        
        Returns:
            连接状态 / Connection status
        """
        try:
            # 执行一个小的测试请求 / Execute a small test request
            test_url = "https://de.indeed.com/jobs?q=test&l="
            
            api_response = await self.client.get({
                "url": test_url,
                "jobPostingNavigation": True,
                "jobPostingNavigationOptions": {"extractFrom": "httpResponseBody"},
            })
            
            return api_response is not None
            
        except Exception as e:
            logger.error(f"Zyte API connection test failed: {e}")
            return False 