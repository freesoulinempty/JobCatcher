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
            # 改进的请求配置以避开反爬虫检测 / Improved request config to avoid anti-bot detection
            api_response = await self.client.get({
                "url": url,
                "jobPostingNavigation": True,
                "jobPostingNavigationOptions": {
                    "extractFrom": "browserHtml"  # 使用浏览器渲染而不是HTTP响应体 / Use browser rendering instead of HTTP response body
                },
                # 浏览器模拟配置 / Browser simulation config
                "browserHtml": True,
                "actions": [
                    {
                        "action": "waitForSelector", 
                        "selector": {
                            "type": "css",
                            "value": ".jobsearch-SerpJobCard"
                        }, 
                        "timeout": 10
                    },
                    {"action": "waitForTimeout", "timeout": 2}  # 等待页面完全加载 / Wait for full page load
                ],
                "screenshot": False,  # 不需要截图以节省成本 / No screenshot to save cost
                "sessionContextParameters": {
                    # 地理位置现在通过IP类型自动处理 / Geolocation is now handled automatically via IP type
                }
            })
            
            job_navigation = api_response.get("jobPostingNavigation", {})
            job_links = []
            
            # 提取职位链接 / Extract job links - 修复字段名从"jobs"改为"items"
            if "items" in job_navigation:
                for job in job_navigation["items"]:
                    if "url" in job:
                        # 确保URL是完整的Indeed链接 / Ensure URL is complete Indeed link
                        job_url = job["url"]
                        if job_url.startswith("/"):
                            job_url = "https://de.indeed.com" + job_url
                        job_links.append(job_url)
            
            logger.info(f"Found {len(job_links)} job links from navigation")
            return job_links
            
        except Exception as e:
            if "520" in str(e) or "521" in str(e):
                logger.warning(f"Indeed anti-bot protection detected (status 520/521). This is normal for job sites. Trying alternative approach...")
                # 尝试备用方法：直接解析HTML / Try alternative: direct HTML parsing
                return await self._fallback_scrape_job_links(url)
            else:
                logger.error(f"Failed to scrape job navigation: {e}")
                return []
    
    async def _fallback_scrape_job_links(self, url: str) -> List[str]:
        """
        备用的职位链接爬取方法 / Fallback job link scraping method
        """
        try:
            # 使用基础浏览器HTML爬取 / Use basic browser HTML scraping
            api_response = await self.client.get({
                "url": url,
                "browserHtml": True,
                "actions": [
                    {"action": "waitForTimeout", "timeout": 3}  # 简单等待 / Simple wait
                ],
                "sessionContextParameters": {
                    # 地理位置自动处理 / Geolocation handled automatically
                }
            })
            
            html_content = api_response.get("browserHtml", "")
            job_links = []
            
            # 简单的HTML解析查找job链接 / Simple HTML parsing for job links
            import re
            job_pattern = r'href="(/viewjob\?jk=[^"]+)"'
            matches = re.findall(job_pattern, html_content)
            
            for match in matches:
                job_url = "https://de.indeed.com" + match
                job_links.append(job_url)
            
            logger.info(f"Fallback method found {len(job_links)} job links")
            return job_links[:25]  # 限制数量 / Limit quantity
            
        except Exception as e:
            logger.error(f"Fallback scraping also failed: {e}")
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
            # 改进的岗位详情爬取配置 / Improved job detail scraping config
            api_response = await self.client.get({
                "url": job_url,
                "jobPosting": True,
                "jobPostingOptions": {
                    "extractFrom": "browserHtml"  # 使用浏览器渲染而不是HTTP响应体 / Use browser rendering instead of HTTP response body
                },
                # 浏览器模拟配置 / Browser simulation config
                "browserHtml": True,
                "actions": [
                    {
                        "action": "waitForSelector", 
                        "selector": {
                            "type": "css",
                            "value": ".jobsearch-JobComponent"
                        }, 
                        "timeout": 10
                    },
                    {"action": "waitForTimeout", "timeout": 1.5}  # 等待内容加载 / Wait for content load
                ],
                "sessionContextParameters": {
                    # 地理位置自动处理 / Geolocation handled automatically
                }
            })
            
            job_posting_data = api_response.get("jobPosting")
            if not job_posting_data:
                # 如果结构化数据提取失败，尝试HTML解析 / If structured extraction fails, try HTML parsing
                html_content = api_response.get("browserHtml", "")
                if html_content:
                    job_posting_data = self._parse_job_from_html(html_content, job_url)
                
            if not job_posting_data:
                return None
                
            # 解析职位数据 / Parse job data
            job_posting = self._parse_indeed_job(job_posting_data, job_url)
            return job_posting
            
        except Exception as e:
            if "520" in str(e) or "521" in str(e):
                logger.warning(f"Job detail protected by anti-bot (520/521): {job_url}")
                # 对于520/521错误，返回基础职位信息 / For 520/521 errors, return basic job info
                return self._create_basic_job_posting(job_url)
            else:
                logger.error(f"Failed to scrape job details from {job_url}: {e}")
                return None
    
    def _parse_job_from_html(self, html_content: str, job_url: str) -> Optional[Dict[str, Any]]:
        """
        从HTML内容解析职位信息 / Parse job information from HTML content
        """
        try:
            import re
            from bs4 import BeautifulSoup
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 提取基础信息 / Extract basic information
            title_elem = soup.find(['h1', 'h2'], class_=re.compile(r'jobsearch-JobInfoHeader-title'))
            company_elem = soup.find(['span', 'div'], class_=re.compile(r'companyName'))
            location_elem = soup.find(['div', 'span'], class_=re.compile(r'companyLocation'))
            description_elem = soup.find(['div'], class_=re.compile(r'jobsearch-jobDescriptionText'))
            
            return {
                "name": title_elem.get_text(strip=True) if title_elem else "Position Available",
                "hiringOrganization": {
                    "name": company_elem.get_text(strip=True) if company_elem else "Company"
                },
                "jobLocation": {
                    "address": {
                        "addressLocality": location_elem.get_text(strip=True) if location_elem else "Germany"
                    }
                },
                "description": description_elem.get_text(strip=True)[:1000] if description_elem else "Job description available on site",
                "url": job_url
            }
            
        except Exception as e:
            logger.error(f"HTML parsing failed: {e}")
            return None
    
    def _create_basic_job_posting(self, job_url: str) -> JobPosting:
        """
        创建基础职位信息 / Create basic job posting
        """
        # 从URL中提取job ID / Extract job ID from URL
        import re
        job_id_match = re.search(r'jk=([^&]+)', job_url)
        job_id = job_id_match.group(1) if job_id_match else "unknown"
        
        return JobPosting(
            id=f"indeed_{job_id}",
            title="Position Available (Protected by Anti-Bot)",
            company_name="Company (Protected)",
            location="Germany",
            employment_type="Unknown",
            description="Job details protected by anti-bot system. Please visit link for details.",
            url=job_url,
            source=JobSource.INDEED,
            scraped_at=datetime.utcnow()
        )
    
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