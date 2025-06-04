"""
用户数据模型 / User data models
"""

from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime


class User(BaseModel):
    """用户基础信息 / User basic information"""
    id: str
    email: EmailStr
    name: str
    picture: Optional[str] = None
    google_id: str
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()
    is_active: bool = True


class UserSession(BaseModel):
    """用户会话信息 / User session information"""
    session_id: str
    user_id: str
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: datetime
    created_at: datetime = datetime.now()


class ResumeAnalysis(BaseModel):
    """简历分析结果 / Resume analysis result"""
    id: str
    user_id: str
    filename: str
    file_content: str
    analysis_result: Dict[str, Any]
    skills: List[str]
    experience_years: Optional[int] = None
    education_level: Optional[str] = None
    languages: List[str]
    preferred_location: Optional[str] = None
    created_at: datetime = datetime.now()


class SkillAnalysis(BaseModel):
    """技能分析结果 / Skill analysis result"""
    skill_name: str
    proficiency_level: str  # "Beginner", "Intermediate", "Advanced", "Expert"
    years_of_experience: Optional[int] = None
    is_core_skill: bool = False


class ResumeUploadRequest(BaseModel):
    """简历上传请求 / Resume upload request"""
    filename: str
    content_type: str


class ChatMessage(BaseModel):
    """聊天消息 / Chat message"""
    id: str
    user_id: str
    message: str
    response: str
    message_type: str  # "text", "resume_upload", "job_recommendation"
    created_at: datetime = datetime.now()


class ChatRequest(BaseModel):
    """聊天请求 / Chat request"""
    message: str
    context: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    """聊天响应 / Chat response"""
    response: str
    message_type: str
    data: Optional[Dict[str, Any]] = None 