"""
职位数据模型 / Job data models
"""

from pydantic import BaseModel, HttpUrl, field_validator
from typing import Optional, List, Union
from datetime import datetime
from enum import Enum


class WorkType(str, Enum):
    """工作方式枚举 / Work type enumeration"""
    FULL_TIME = "Full-time"
    PART_TIME = "Part-time"
    CONTRACT = "Contract"
    INTERNSHIP = "Internship"
    REMOTE = "Remote"
    HYBRID = "Hybrid"
    ON_SITE = "On-site"


class ExperienceLevel(str, Enum):
    """经验级别枚举 / Experience level enumeration"""
    ENTRY_LEVEL = "Entry level"
    MID_SENIOR_LEVEL = "Mid-Senior level"
    SENIOR_LEVEL = "Senior level"
    EXECUTIVE = "Executive"
    INTERNSHIP = "Internship"


class JobSource(str, Enum):
    """职位来源枚举 / Job source enumeration"""
    LINKEDIN = "LinkedIn"
    INDEED = "Indeed"
    STEPSTONE = "StepStone"


class JobPosting(BaseModel):
    """职位发布信息 / Job posting information"""
    id: str
    title: str
    company_name: str
    company_url: Optional[HttpUrl] = None
    location: str
    work_type: Optional[WorkType] = None
    contract_type: Optional[str] = None
    experience_level: Optional[ExperienceLevel] = None
    sector: Optional[str] = None
    salary: Optional[str] = None
    description: str
    url: Optional[HttpUrl] = None
    apply_url: Optional[HttpUrl] = None
    posted_date: Optional[datetime] = None
    posted_time_ago: Optional[str] = None
    applications_count: Optional[str] = None
    source: JobSource
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

    @field_validator('url', 'apply_url', 'company_url', mode='before')
    @classmethod
    def validate_url_fields(cls, v):
        """验证URL字段，处理空字符串 / Validate URL fields, handle empty strings"""
        if v == '' or v is None:
            return None
        return v


class JobSearchRequest(BaseModel):
    """职位搜索请求 / Job search request"""
    keywords: str  # 🔥 修正字段名：job_title -> keywords / Fixed field name: job_title -> keywords
    city: Optional[str] = None  # 🔥 修正字段名：location -> city / Fixed field name: location -> city
    max_results: int = 25


class JobSearchResponse(BaseModel):
    """职位搜索响应 / Job search response"""
    jobs: List[JobPosting]
    total_count: int
    query: str
    location: Optional[str] = None


class JobMatch(BaseModel):
    """职位匹配结果 / Job match result"""
    job: JobPosting
    match_score: float
    match_reasons: List[str]
    skill_matches: List[str]
    location_match: bool
    experience_match: bool


class JobRecommendationResponse(BaseModel):
    """职位推荐响应 / Job recommendation response"""
    matches: List[JobMatch]
    total_count: int
    analysis_summary: str 