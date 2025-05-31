"""
JobCatcher主应用入口 / JobCatcher main application entry
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging
import os

from app.core.config import settings
from app.database.connection import init_databases
from app.services.scheduler_service import SchedulerService
from app.api import auth, jobs, chat, upload

# 配置日志 / Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(settings.log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理 / Application lifespan management"""
    try:
        # 启动时初始化 / Initialize on startup
        logger.info("Starting JobCatcher application...")
        
        # 创建必要的目录 / Create necessary directories
        os.makedirs("data", exist_ok=True)
        os.makedirs("logs", exist_ok=True)
        os.makedirs("uploads", exist_ok=True)
        
        # 初始化数据库 / Initialize databases
        db_connections = await init_databases()
        app.state.db_connections = db_connections
        
        # 启动定时任务服务 / Start scheduler service
        scheduler_service = SchedulerService()
        await scheduler_service.start()
        app.state.scheduler_service = scheduler_service
        
        logger.info("JobCatcher application started successfully")
        yield
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
    finally:
        # 关闭时清理 / Cleanup on shutdown
        logger.info("Shutting down JobCatcher application...")
        
        # 停止定时任务服务 / Stop scheduler service
        if hasattr(app.state, 'scheduler_service'):
            await app.state.scheduler_service.stop()


# 创建FastAPI应用实例 / Create FastAPI application instance
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="基于Claude 4 Sonnet驱动的智能职位搜索和匹配平台 / Intelligent job search and matching platform powered by Claude 4 Sonnet",
    lifespan=lifespan
)

# 配置CORS中间件 / Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins.split(","),  # 从配置文件读取 / Read from config file
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# 挂载静态文件 / Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# 包含路由 / Include routers
app.include_router(auth.router, prefix="/api", tags=["Authentication"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["Jobs"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(upload.router, prefix="/api/upload", tags=["Upload"])


@app.get("/")
async def root():
    """根路径健康检查 / Root path health check"""
    return {
        "message": "JobCatcher API is running",
        "version": settings.app_version,
        "status": "healthy"
    }


@app.get("/health")
async def health_check():
    """健康检查端点 / Health check endpoint"""
    try:
        # 检查数据库连接 / Check database connections
        db_connections = getattr(app.state, 'db_connections', None)
        if not db_connections:
            raise HTTPException(status_code=503, detail="Database not initialized")
        
        # 检查定时任务服务 / Check scheduler service
        scheduler_service = getattr(app.state, 'scheduler_service', None)
        scheduler_status = "running" if scheduler_service and scheduler_service.scheduler.running else "stopped"
        
        return {
            "status": "healthy",
            "version": settings.app_version,
            "databases": {
                "chroma": "connected" if db_connections.get('chroma_client') else "disconnected",
                "sqlite": "connected"
            },
            "scheduler": scheduler_status
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")


@app.post("/admin/trigger-crawl")
async def trigger_manual_crawl():
    """手动触发爬取任务 / Manually trigger crawling task"""
    try:
        scheduler_service = getattr(app.state, 'scheduler_service', None)
        if not scheduler_service:
            raise HTTPException(status_code=503, detail="Scheduler service not available")
        
        result = await scheduler_service.trigger_manual_crawl()
        return result
        
    except Exception as e:
        logger.error(f"Manual crawl trigger failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger crawl: {str(e)}")


@app.post("/admin/trigger-cleanup")
async def trigger_manual_cleanup():
    """手动触发清理任务 / Manually trigger cleanup task"""
    try:
        scheduler_service = getattr(app.state, 'scheduler_service', None)
        if not scheduler_service:
            raise HTTPException(status_code=503, detail="Scheduler service not available")
        
        result = await scheduler_service.trigger_manual_cleanup()
        return result
        
    except Exception as e:
        logger.error(f"Manual cleanup trigger failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger cleanup: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.backend_port,
        reload=settings.debug
    ) 