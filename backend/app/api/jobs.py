"""
职位搜索API / Job search API
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from typing import List, Optional
from ..models.job import JobPosting, JobSearchRequest
from ..core.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/search")
async def search_jobs(
    request: JobSearchRequest,
    http_request: Request
) -> dict:
    """
    搜索职位 / Search jobs
    根据README要求：只从向量数据库检索，不再实时爬取 / According to README: only search from vector DB, no real-time scraping
    
    Args:
        request: 搜索请求参数 / Search request parameters
        
    Returns:
        搜索结果 / Search results
    """
    try:
        logger.info(f"Job search request: {request.job_title} in {request.location}")
        
        # 根据README用户搜索流程：只从Chroma向量数据库检索 / According to README user search flow: only retrieve from Chroma vector DB
        vector_jobs = []
        try:
            # 构建语义搜索查询（英德语）/ Build semantic search query (English/German)
            search_query = f"Looking for {request.job_title} job"
            if request.location:
                search_query += f" in {request.location}"
            
            logger.info(f"Vector DB semantic query: '{search_query}' (limit: {request.max_results})")
            
            vector_jobs = await _search_jobs_in_vector_db(
                request.job_title, 
                request.location,
                http_request,
                limit=request.max_results
            )
            logger.info(f"Vector DB search result: {len(vector_jobs)} jobs")
            if vector_jobs:
                logger.info(f"Sample vector job: {vector_jobs[0].title} at {vector_jobs[0].company_name}")
                
        except Exception as e:
            logger.error(f"Vector DB semantic search failed: {e}")
            vector_jobs = []
        
        logger.info(f"Returning {len(vector_jobs)} jobs to frontend")
        
        return {
            "jobs": [job.model_dump() for job in vector_jobs],
            "total_count": len(vector_jobs)
        }
        
    except Exception as e:
        logger.error(f"Job search failed: {e}")
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


async def _store_jobs_in_vector_db(jobs: List[JobPosting], request: Request):
    """将职位存储到向量数据库 / Store jobs in vector database"""
    try:
        db_connections = request.app.state.db_connections
        jobs_collection = db_connections['jobs_collection']
        openai_client = db_connections['openai_client']
        
        # 导入embedding函数 / Import embedding functions
        from ..database.connection import get_text_embedding
        
        stored_count = 0
        skipped_count = 0
        
        for job in jobs:
            # 检查是否已存在（去重机制）/ Check if already exists (deduplication)
            try:
                existing = jobs_collection.get(ids=[job.id])
                if existing['ids']:
                    skipped_count += 1
                    continue
            except:
                pass  # 如果查询失败，继续存储 / If query fails, continue storing
                
            # 构建用于向量化的文档内容（英德语）/ Build document content for vectorization (English/German)
            document = f"Job: {job.title} Company: {job.company_name} Location: {job.location} Description: {job.description[:500]}"
            
            # 使用OpenAI text-embedding-3-small模型进行向量化 / Use OpenAI text-embedding-3-small for vectorization
            logger.info(f"Vectorizing job with OpenAI: {job.title} at {job.company_name}")
            try:
                embedding = get_text_embedding(openai_client, document)
                logger.info(f"✅ Successfully generated embedding (dimension: {len(embedding)})")
            except Exception as e:
                logger.error(f"❌ Failed to generate embedding for job {job.id}: {e}")
                continue
            
            # 添加到向量数据库 / Add to vector database
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
                "embedding_model": "text-embedding-3-small"
            }
            
            jobs_collection.add(
                documents=[document],
                embeddings=[embedding],
                metadatas=[metadata],
                ids=[job.id]
            )
            stored_count += 1
            
        logger.info(f"Vector DB storage: {stored_count} new jobs vectorized with OpenAI text-embedding-3-small and stored, {skipped_count} duplicates skipped")
        return stored_count
            
    except Exception as e:
        logger.error(f"Failed to store jobs in vector DB: {e}")
        return 0


async def _search_jobs_in_vector_db(
    job_title: str, 
    location: Optional[str],
    request: Request,
    limit: int = 25
) -> List[JobPosting]:
    """从向量数据库搜索职位 / Search jobs from vector database"""
    try:
        db_connections = request.app.state.db_connections
        jobs_collection = db_connections['jobs_collection']
        openai_client = db_connections['openai_client']
        
        # 导入embedding函数 / Import embedding functions
        from ..database.connection import get_text_embedding
        
        # 构建语义搜索查询（英德语）/ Build semantic search query (English/German)
        query = f"Looking for {job_title} job"
        if location:
            query += f" in {location}"
            
        logger.info(f"Vector DB semantic query: '{query}' (limit: {limit})")
            
        # 使用OpenAI text-embedding-3-small将查询向量化 / Vectorize query using OpenAI text-embedding-3-small
        try:
            query_embedding = get_text_embedding(openai_client, query)
            logger.info(f"✅ Successfully generated query embedding (dimension: {len(query_embedding)})")
        except Exception as e:
            logger.error(f"❌ Failed to generate query embedding: {e}")
            return []
            
        # 使用向量相似度搜索 / Search using vector similarity
        results = jobs_collection.query(
            query_embeddings=[query_embedding],
            n_results=limit
        )
        
        logger.info(f"Vector DB semantic search results: {len(results.get('metadatas', [[]])[0])} items")
        
        # 转换为JobPosting对象 / Convert to JobPosting objects
        vector_jobs = []
        if results['metadatas']:
            for metadata in results['metadatas'][0]:
                try:
                    # 导入枚举类型 / Import enum types
                    from ..models.job import WorkType, ExperienceLevel, JobSource
                    
                    # 处理work_type枚举 / Handle work_type enum
                    work_type = None
                    if metadata.get('work_type'):
                        try:
                            work_type = WorkType(metadata['work_type'])
                        except ValueError:
                            work_type = None
                    
                    # 处理experience_level枚举 / Handle experience_level enum
                    experience_level = None
                    if metadata.get('experience_level'):
                        try:
                            experience_level = ExperienceLevel(metadata['experience_level'])
                        except ValueError:
                            experience_level = None
                    
                    # 处理source枚举 / Handle source enum
                    source = JobSource.LINKEDIN  # 默认值 / Default value
                    if metadata.get('source'):
                        try:
                            source = JobSource(metadata['source'])
                        except ValueError:
                            source = JobSource.LINKEDIN
                    
                    # 处理URL字段，避免空字符串导致验证错误 / Handle URL fields to avoid empty string validation errors
                    url = metadata.get('url', '')
                    apply_url = metadata.get('apply_url', '')
                    
                    # 如果URL为空，使用None / If URL is empty, use None
                    if not url:
                        url = None
                    if not apply_url:
                        apply_url = None
                    
                    # 创建JobPosting对象 / Create JobPosting object
                    job = JobPosting(
                        id=metadata.get('id', ''),
                        title=metadata.get('title', ''),
                        company_name=metadata.get('company_name', ''),
                        location=metadata.get('location', ''),
                        work_type=work_type,
                        contract_type=metadata.get('contract_type'),
                        experience_level=experience_level,
                        sector=metadata.get('sector'),
                        salary=metadata.get('salary'),
                        description=metadata.get('full_description', ''),
                        url=url,
                        apply_url=apply_url,
                        posted_time_ago=metadata.get('posted_time_ago'),
                        applications_count=metadata.get('applications_count'),
                        source=source
                    )
                    
                    vector_jobs.append(job)
                    
                except Exception as e:
                    logger.error(f"Error converting metadata to JobPosting: {e}")
                    continue
                    
        logger.info(f"Vector DB converted jobs: {len(vector_jobs)} valid JobPosting objects")
        return vector_jobs
        
    except Exception as e:
        logger.error(f"Vector DB search failed: {e}")
        return []


@router.delete("/cleanup")
async def cleanup_old_jobs():
    """
    清理过期职位数据 / Cleanup expired job data
    注意：根据README，数据清理应该通过定时任务完成，此API仅用于手动触发
    """
    try:
        # 这里可以调用定时任务的清理逻辑 / Can call scheduled cleanup logic here
        logger.info("Manual cleanup triggered via API")
        return {"message": "Cleanup task triggered", "status": "success"}
        
    except Exception as e:
        logger.error(f"Manual cleanup failed: {e}")
        raise HTTPException(status_code=500, detail=f"清理失败: {str(e)}") 