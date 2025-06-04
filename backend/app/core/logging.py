"""
高级日志配置系统 / Advanced logging configuration system
支持token监控、性能分析、错误跟踪 / Support token monitoring, performance analysis, error tracking
"""

import logging
import logging.handlers
import json
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from pathlib import Path

class TokenUsageFormatter(logging.Formatter):
    """Token使用量专用格式化器 / Token usage specialized formatter"""
    
    def format(self, record):
        # 基础格式 / Basic format
        formatted = super().format(record)
        
        # 如果是token相关日志，添加特殊标记 / Add special marker for token-related logs
        if hasattr(record, 'token_info'):
            token_info = record.token_info
            token_summary = f"[TOKENS: Input:{token_info.get('input_tokens', 0)}, Output:{token_info.get('output_tokens', 0)}, Cost:${token_info.get('estimated_cost', 0):.4f}]"
            formatted = f"{formatted} {token_summary}"
        
        return formatted

class PerformanceFormatter(logging.Formatter):
    """性能监控专用格式化器 / Performance monitoring specialized formatter"""
    
    def format(self, record):
        formatted = super().format(record)
        
        # 如果是性能相关日志，添加耗时信息 / Add duration info for performance logs
        if hasattr(record, 'duration'):
            duration_info = f"[PERF: {record.duration:.3f}s]"
            formatted = f"{formatted} {duration_info}"
        
        return formatted

class JobCatcherLogger:
    """JobCatcher专用日志系统 / JobCatcher specialized logging system"""
    
    def __init__(self, app_name: str = "JobCatcher"):
        self.app_name = app_name
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        
        # 配置不同类型的日志记录器 / Configure different types of loggers
        self.setup_main_logger()
        self.setup_token_logger()
        self.setup_performance_logger()
        self.setup_error_logger()
        self.setup_api_logger()
        
    def setup_main_logger(self):
        """设置主日志记录器 / Setup main logger"""
        logger = logging.getLogger(self.app_name)
        logger.setLevel(logging.INFO)
        
        # 控制台处理器 / Console handler
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # 文件处理器 / File handler
        file_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "jobcatcher.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    def setup_token_logger(self):
        """设置token使用量日志记录器 / Setup token usage logger"""
        logger = logging.getLogger(f"{self.app_name}.tokens")
        logger.setLevel(logging.INFO)
        
        # Token专用文件处理器 / Token-specific file handler
        token_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "token_usage.log",
            maxBytes=5*1024*1024,  # 5MB
            backupCount=10,
            encoding='utf-8'
        )
        token_formatter = TokenUsageFormatter(
            '%(asctime)s - TOKEN_USAGE - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        token_handler.setFormatter(token_formatter)
        logger.addHandler(token_handler)
        
        # 不再添加CSV处理器，CSV由log_token_usage函数直接写入
        # No longer add CSV handler, CSV is written directly by log_token_usage function
        
        # 确保CSV文件存在并有标题 / Ensure CSV file exists with header
        csv_file = self.log_dir / "token_usage.csv"
        if not csv_file.exists():
            with open(csv_file, 'w', encoding='utf-8') as f:
                f.write("timestamp,session_id,model,input_tokens,output_tokens,total_tokens,cost_usd,task_type,user_message_length\n")
    
    def setup_performance_logger(self):
        """设置性能监控日志记录器 / Setup performance monitoring logger"""
        logger = logging.getLogger(f"{self.app_name}.performance")
        logger.setLevel(logging.INFO)
        
        perf_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "performance.log",
            maxBytes=5*1024*1024,  # 5MB
            backupCount=5,
            encoding='utf-8'
        )
        perf_formatter = PerformanceFormatter(
            '%(asctime)s - PERFORMANCE - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        perf_handler.setFormatter(perf_formatter)
        logger.addHandler(perf_handler)
    
    def setup_error_logger(self):
        """设置错误日志记录器 / Setup error logger"""
        logger = logging.getLogger(f"{self.app_name}.errors")
        logger.setLevel(logging.ERROR)
        
        error_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "errors.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=10,
            encoding='utf-8'
        )
        error_formatter = logging.Formatter(
            '%(asctime)s - ERROR - %(name)s - %(funcName)s:%(lineno)d - %(message)s\n%(exc_info)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        error_handler.setFormatter(error_formatter)
        logger.addHandler(error_handler)
    
    def setup_api_logger(self):
        """设置API访问日志记录器 / Setup API access logger"""
        logger = logging.getLogger(f"{self.app_name}.api")
        logger.setLevel(logging.INFO)
        
        api_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "api_access.log",
            maxBytes=20*1024*1024,  # 20MB
            backupCount=5,
            encoding='utf-8'
        )
        api_formatter = logging.Formatter(
            '%(asctime)s - API - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        api_handler.setFormatter(api_formatter)
        logger.addHandler(api_handler)

def log_token_usage(
    session_id: str,
    model: str, 
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
    task_type: str = "unknown",
    user_message_length: int = 0
):
    """记录token使用量到专用日志 / Log token usage to specialized log"""
    # JSON格式记录到token_usage.log / JSON format to token_usage.log
    token_logger = logging.getLogger("JobCatcher.tokens")
    
    log_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "cost_usd": cost_usd,
        "task_type": task_type,
        "user_message_length": user_message_length
    }
    
    # 记录到JSON日志 / Log to JSON log
    token_logger.info(
        json.dumps(log_data),
        extra={
            "tokens": f"Input:{input_tokens}, Output:{output_tokens}, Cost:${cost_usd:.4f}"
        }
    )
    
    # CSV格式直接写入文件 / Write CSV format directly to file
    csv_line = f"{log_data['timestamp']},{session_id},{model},{input_tokens},{output_tokens},{input_tokens + output_tokens},{cost_usd:.6f},{task_type},{user_message_length}"
    
    # 直接写入CSV文件，避免重复记录 / Write directly to CSV file to avoid duplicate logging
    csv_file = os.path.join(os.path.dirname(__file__), "../../logs/token_usage.csv")
    try:
        with open(csv_file, 'a', encoding='utf-8') as f:
            f.write(csv_line + '\n')
    except Exception as e:
        token_logger.error(f"Failed to write CSV: {e}")

def log_performance(operation: str, duration: float, details: Optional[Dict[str, Any]] = None):
    """记录性能信息到专用日志 / Log performance info to specialized log"""
    perf_logger = logging.getLogger("JobCatcher.performance")
    
    log_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "operation": operation,
        "duration_seconds": duration,
        "details": details or {}
    }
    
    record = perf_logger.makeRecord(
        name=perf_logger.name,
        level=logging.INFO,
        fn="",
        lno=0,
        msg=f"{operation} completed",
        args=(),
        exc_info=None
    )
    record.duration = duration
    perf_logger.handle(record)

def log_api_access(
    method: str,
    endpoint: str, 
    status_code: int,
    duration: float,
    user_agent: str = "",
    ip_address: str = ""
):
    """记录API访问日志 / Log API access"""
    api_logger = logging.getLogger("JobCatcher.api")
    
    log_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "method": method,
        "endpoint": endpoint,
        "status_code": status_code,
        "duration_ms": duration * 1000,
        "user_agent": user_agent,
        "ip_address": ip_address
    }
    
    api_logger.info(json.dumps(log_data, ensure_ascii=False))

def log_error_with_context(error: Exception, context: Dict[str, Any]):
    """记录错误及上下文信息 / Log error with context"""
    error_logger = logging.getLogger("JobCatcher.errors")
    
    error_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "error_type": type(error).__name__,
        "error_message": str(error),
        "context": context
    }
    
    error_logger.error(json.dumps(error_data, ensure_ascii=False), exc_info=error)

# 初始化日志系统 / Initialize logging system
jobcatcher_logger = JobCatcherLogger()

def get_logger(name: str = "JobCatcher") -> logging.Logger:
    """获取日志记录器 / Get logger"""
    return logging.getLogger(name) 