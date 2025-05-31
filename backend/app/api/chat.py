"""
AI聊天API / AI chat API
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from typing import Optional
import logging
import json

from ..models.user import ChatRequest, ChatResponse
from ..services.claude_service import ClaudeService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/message")
async def chat_message(request: ChatRequest):
    """
    发送聊天消息 / Send chat message
    
    Args:
        request: 聊天请求 / Chat request
        
    Returns:
        聊天响应 / Chat response
    """
    try:
        claude_service = ClaudeService()
        
        # 非流式响应（用于简单消息）/ Non-streaming response (for simple messages)
        response_content = ""
        async for chunk in claude_service.chat_stream(request.message, request.context):
            response_content += chunk
            
        return ChatResponse(
            response=response_content,
            message_type="text",
            data=request.context
        )
        
    except Exception as e:
        logger.error(f"Chat message failed: {e}")
        raise HTTPException(status_code=500, detail=f"聊天失败: {str(e)}")


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """
    流式聊天 / Streaming chat
    
    Args:
        request: 聊天请求 / Chat request
        
    Returns:
        流式聊天响应 / Streaming chat response
    """
    try:
        claude_service = ClaudeService()
        
        async def generate_response():
            """生成流式响应 / Generate streaming response"""
            try:
                async for chunk in claude_service.chat_stream(request.message, request.context):
                    # 格式化为SSE格式 / Format as SSE
                    yield f"data: {json.dumps({'content': chunk, 'type': 'text'})}\n\n"
                    
                # 发送结束信号 / Send end signal
                yield f"data: {json.dumps({'content': '[DONE]', 'type': 'end'})}\n\n"
                
            except Exception as e:
                logger.error(f"Streaming error: {e}")
                yield f"data: {json.dumps({'content': f'Error: {str(e)}', 'type': 'error'})}\n\n"
        
        return StreamingResponse(
            generate_response(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )
        
    except Exception as e:
        logger.error(f"Streaming chat failed: {e}")
        raise HTTPException(status_code=500, detail=f"流式聊天失败: {str(e)}")


@router.post("/analyze-resume")
async def analyze_resume(
    user_id: str,
    resume_content: str,
    filename: str,
    request: Request
):
    """
    分析简历并推荐职位 / Analyze resume and recommend jobs
    
    Args:
        user_id: 用户ID / User ID
        resume_content: 简历内容 / Resume content
        filename: 文件名 / Filename
        
    Returns:
        简历分析和职位推荐 / Resume analysis and job recommendations
    """
    try:
        claude_service = ClaudeService()
        
        # 分析简历 / Analyze resume
        logger.info(f"Analyzing resume for user: {user_id}")
        analysis_result = await claude_service.analyze_resume(resume_content, filename)
        
        if analysis_result.get('error'):
            raise HTTPException(status_code=400, detail=f"简历分析失败: {analysis_result['error']}")
        
        # 从向量数据库搜索相关职位 / Search relevant jobs from vector database
        db_connections = request.app.state.db_connections
        jobs_collection = db_connections['jobs_collection']
        
        # 基于简历技能搜索职位 / Search jobs based on resume skills
        skills_query = " ".join(analysis_result.get('skills', []))
        location_query = analysis_result.get('preferred_location', '')
        
        query = f"{skills_query} {location_query}".strip()
        if not query:
            query = "software engineer developer"  # 默认查询 / Default query
            
        # 搜索相关职位 / Search relevant jobs
        job_results = jobs_collection.query(
            query_texts=[query],
            n_results=25
        )
        
        # 构建职位对象列表 / Build job objects list
        from ..models.job import JobPosting, JobSource
        jobs = []
        if job_results['metadatas']:
            for metadata in job_results['metadatas'][0]:
                try:
                    job = JobPosting(
                        id=metadata['id'],
                        title=metadata['title'],
                        company_name=metadata['company_name'],
                        location=metadata['location'],
                        description="",
                        url=metadata['url'],
                        source=JobSource(metadata['source'])
                    )
                    jobs.append(job)
                except:
                    continue
        
        # 使用Claude匹配职位 / Use Claude to match jobs
        job_matches = []
        if jobs:
            job_matches = await claude_service.match_jobs_with_resume(analysis_result, jobs)
        
        # TODO: 存储简历分析结果到数据库 / Store resume analysis to database
        
        return {
            "analysis": analysis_result,
            "job_matches": [
                {
                    "job": match.job.dict(),
                    "match_score": match.match_score,
                    "match_reasons": match.match_reasons,
                    "skill_matches": match.skill_matches,
                    "location_match": match.location_match,
                    "experience_match": match.experience_match
                }
                for match in job_matches
            ],
            "message_type": "resume_analysis",
            "total_matches": len(job_matches)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Resume analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"简历分析失败: {str(e)}")


@router.get("/skill-heatmap/{job_title}")
async def generate_skill_heatmap(job_title: str):
    """
    生成技能热点图 / Generate skill heatmap
    
    Args:
        job_title: 职位标题 / Job title
        
    Returns:
        技能热点图数据 / Skill heatmap data
    """
    try:
        claude_service = ClaudeService()
        heatmap_data = await claude_service.generate_skill_heatmap_data(job_title)
        
        return {
            "heatmap_data": heatmap_data,
            "message_type": "skill_heatmap"
        }
        
    except Exception as e:
        logger.error(f"Skill heatmap generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"技能热点图生成失败: {str(e)}")


@router.get("/history/{user_id}")
async def get_chat_history(user_id: str, limit: int = 20):
    """
    获取聊天历史 / Get chat history
    
    Args:
        user_id: 用户ID / User ID
        limit: 限制数量 / Limit count
        
    Returns:
        聊天历史 / Chat history
    """
    try:
        # TODO: 从数据库获取聊天历史 / Get chat history from database
        
        return {
            "messages": [],
            "total_count": 0,
            "user_id": user_id
        }
        
    except Exception as e:
        logger.error(f"Failed to get chat history: {e}")
        raise HTTPException(status_code=500, detail=f"获取聊天历史失败: {str(e)}") 