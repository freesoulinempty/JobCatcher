"""
JobCatcher 核心配置文件 / Core configuration file
所有配置从.env文件读取，无硬编码默认值 / All configurations read from .env file, no hardcoded defaults
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """应用配置类 / Application settings class"""
    
    # 应用基础配置 / Basic app configuration
    app_name: str
    app_version: str
    debug: bool
    secret_key: str
    
    # 服务端口 / Service ports
    backend_port: int
    frontend_port: int
    
    # 数据库配置 / Database Configuration
    database_url: str
    
    # JWT配置 / JWT Configuration
    jwt_secret_key: str
    jwt_algorithm: str
    jwt_access_token_expire_minutes: int
    
    # OpenAI配置 / OpenAI Configuration
    openai_api_key: str
    
    # Claude 4 Sonnet API配置 / Claude 4 Sonnet API configuration
    anthropic_api_key: str
    claude_model: str
    
    # Google OAuth配置 / Google OAuth configuration
    google_client_id: str
    google_client_secret: str
    google_redirect_uri: str
    
    # Apify API配置 / Apify API configuration
    apify_api_token: str
    apify_linkedin_actor_id: str
    apify_base_url: str
    
    # Zyte API配置 / Zyte API configuration
    zyte_api_key: str
    zyte_api_url: str
    
    # CORS配置 / CORS Configuration
    allowed_origins: str
    
    # 爬取策略配置 / Crawling strategy configuration
    crawl_cache_ttl_hours: int
    crawl_linkedin_cache_ttl_hours: int
    crawl_max_jobs_per_source: int
    crawl_cache_hit_rate_target: float
    crawl_force_refresh_probability: float
    crawl_linkedin_refresh_probability: float
    
    # 日志配置 / Logging configuration
    log_level: str
    log_file: str
    
    # 配置文件设置 / Configuration file settings
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="forbid"  # 禁止额外字段，确保配置严格 / Forbid extra fields for strict configuration
    )


# 全局配置实例 / Global settings instance
settings = Settings() 