"""
AI聊天API / AI chat API
统一的智能聊天接口，支持工具调用 / Unified intelligent chat interface with tool calling
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from typing import Optional, Dict, Any
import logging
import json
import uuid
import time

from ..models.user import ChatRequest, ChatResponse
from ..services.claude_service import ClaudeService
from ..core.logging import log_api_access, log_performance, log_error_with_context, get_logger

logger = get_logger("JobCatcher.api.chat")
router = APIRouter()

# 全局ClaudeService实例，保持会话状态 / Global ClaudeService instance to maintain session state
_global_claude_service = None

def get_claude_service() -> ClaudeService:
    """获取全局ClaudeService实例 / Get global ClaudeService instance"""
    global _global_claude_service
    if _global_claude_service is None:
        _global_claude_service = ClaudeService()
        logger.info("Created global ClaudeService instance for session management")
    return _global_claude_service

@router.post("/unified")
async def unified_chat(request: ChatRequest, http_request: Request = None):
    """
    统一智能聊天接口 / Unified intelligent chat interface
    支持文件上传、简历分析、职位推荐、技能热点图等所有功能
    
    Args:
        request: 聊天请求 / Chat request
        http_request: HTTP请求对象 / HTTP request object
        
    Returns:
        统一聊天响应 / Unified chat response
    """
    try:
        claude_service = get_claude_service()
        
        # 获取或生成会话ID / Get or generate session ID
        session_id = None
        if request.session_id:
            session_id = request.session_id
        elif request.context and 'session_id' in request.context:
            session_id = request.context['session_id']
        else:
            session_id = str(uuid.uuid4())
            
        logger.info(f"Chat API: Using session_id = {session_id}")
        
        # 准备上下文 / Prepare context
        context = request.context or {}
        
        # 如果有文件上传，添加到上下文 / If file uploaded, add to context
        if request.context and request.context.get('file_content'):
            context['file_content'] = request.context['file_content']
            context['filename'] = request.context.get('filename', 'unknown')
            context['resume_uploaded'] = True
        elif request.context and request.context.get('uploaded_file'):
            # 处理通过文件上传API上传的文件 / Handle files uploaded via upload API
            uploaded_file = request.context['uploaded_file']
            
            # 🔥 修复：使用新的document_data格式 / FIX: Use new document_data format
            if uploaded_file.get('document_data'):
                context['uploaded_file'] = uploaded_file
                context['resume_uploaded'] = True
                logger.info(f"📄 Using new document_data format for file: {uploaded_file.get('filename', 'unknown')}")
            else:
                # 向后兼容旧格式 / Backward compatibility with old format
                context['file_content'] = uploaded_file.get('text_content', '')
                context['filename'] = uploaded_file.get('filename', 'unknown')
                context['file_path'] = uploaded_file.get('file_path', '')
                context['resume_uploaded'] = True
                logger.info(f"📄 Using legacy format for file: {uploaded_file.get('filename', 'unknown')}")
        
        # 🔥 README步骤4：基于简历向量查询匹配职位 / README step 4: Query matching jobs based on resume vector
        if http_request and hasattr(http_request, 'app'):
            db_connections = http_request.app.state.db_connections
            if 'jobs_collection' in db_connections and 'resumes_collection' in db_connections and 'openai_client' in db_connections:
                jobs_collection = db_connections['jobs_collection']
                resumes_collection = db_connections['resumes_collection']
                openai_client = db_connections['openai_client']
                
                try:
                    # 🔥 检查是否有简历向量可用于智能匹配 / Check if resume vector is available for smart matching
                    user_id = context.get('session_id', 'unknown')  # 使用session_id作为用户标识
                    resume_vector = None
                    resume_analysis = None
                    
                    # 尝试获取用户最新的简历向量 / Try to get user's latest resume vector
                    try:
                        user_resumes = resumes_collection.query(
                            query_embeddings=[[0.0] * 1536],  # 虚拟查询获取用户简历
                            n_results=10,
                            where={"user_id": user_id},
                            include=['embeddings', 'metadatas']  # 🔥 关键修复：明确包含embeddings
                        )
                        
                        if (user_resumes.get('embeddings') and 
                            len(user_resumes['embeddings']) > 0 and 
                            user_resumes['embeddings'][0] is not None and 
                            len(user_resumes['embeddings'][0]) > 0):
                            # 使用最新简历向量 / Use latest resume vector
                            resume_vector = user_resumes['embeddings'][0][0]  # 最新的简历向量
                            resume_metadata = user_resumes['metadatas'][0][0]
                            
                            # 重建简历分析数据 / Rebuild resume analysis data
                            import json
                            resume_analysis = {
                                "skills": json.loads(resume_metadata.get('skills', '[]')),
                                "experience_years": resume_metadata.get('experience_years', 0),
                                "location": resume_metadata.get('location', ''),
                                "education_level": resume_metadata.get('education_level', ''),
                                "languages": json.loads(resume_metadata.get('languages', '[]')),
                                "summary": resume_metadata.get('summary', '')
                            }
                            
                            logger.info(f"💼 Using user resume vector for personalized job matching: {user_id}")
                    except Exception as e:
                        logger.info(f"No user resume found, using general query: {e}")
                    
                    # 🔥 智能职位查询：优先使用简历向量，否则使用通用查询 / Smart job query: prefer resume vector, fallback to general query
                    if resume_vector is not None:
                        # 基于简历向量的个性化匹配 / Personalized matching based on resume vector
                        job_results = jobs_collection.query(
                            query_embeddings=[resume_vector],
                            n_results=25  # README要求：返回25个职位
                        )
                        match_type = "personalized"
                    else:
                        # 通用职位查询（回退方案）/ General job query (fallback)
                        from ..database.connection import get_text_embedding
                        query_text = "software engineer developer germany"
                        query_embedding = get_text_embedding(openai_client, query_text)
                        
                        job_results = jobs_collection.query(
                            query_embeddings=[query_embedding],
                            n_results=25
                        )
                        match_type = "general"
                    
                    # 构建职位列表 / Build job list
                    if job_results['metadatas']:
                        jobs = []
                        for metadata in job_results['metadatas'][0]:
                            try:
                                job_data = {
                                    "id": metadata.get('id', ''),
                                    "title": metadata.get('title', ''),
                                    "company_name": metadata.get('company_name', ''),
                                    "location": metadata.get('location', ''),
                                    "description": metadata.get('description', ''),
                                    "url": metadata.get('url', ''),
                                    "job_type": metadata.get('job_type', '未知')
                                }
                                jobs.append(job_data)
                            except:
                                continue
                        
                        if jobs:
                            context['job_postings'] = jobs
                            context['match_type'] = match_type
                            context['resume_analysis'] = resume_analysis  # 传递简历分析数据
                            logger.info(f"💼 Enhanced message with job postings context for session {session_id}: {len(jobs)} jobs ({match_type} matching)")
                            
                except Exception as e:
                    logger.warning(f"Failed to fetch job data: {e}")
        
        async def generate_response():
            """生成统一流式响应 / Generate unified streaming response"""
            import json  # 🔥 修复作用域问题：在嵌套函数中重新导入json
            try:
                # 使用统一的Claude服务 / Use unified Claude service
                async for event in claude_service.chat_stream_unified(
                    request.message, 
                    context, 
                    session_id
                ):
                    # 转换事件格式 / Convert event format
                    response_event = {
                        "session_id": session_id,
                        "timestamp": event.get("timestamp", ""),
                        **event
                    }
                    
                    yield f"data: {json.dumps(response_event)}\n\n"
                    
                # 发送结束信号 / Send end signal
                yield f"data: {json.dumps({'type': 'complete', 'session_id': session_id})}\n\n"
                
            except Exception as e:
                logger.error(f"Unified streaming error: {e}")
                yield f"data: {json.dumps({'type': 'error', 'content': f'Error: {str(e)}', 'session_id': session_id})}\n\n"
        
        return StreamingResponse(
            generate_response(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*"
            }
        )
        
    except Exception as e:
        logger.error(f"Unified chat failed: {e}")
        raise HTTPException(status_code=500, detail=f"统一聊天失败: {str(e)}")


@router.post("/message")
async def chat_message(request: ChatRequest, http_request: Request = None):
    """
    非流式聊天消息 / Non-streaming chat message
    兼容旧接口 / Backward compatibility
    
    Args:
        request: 聊天请求 / Chat request
        http_request: HTTP请求对象 / HTTP request object
        
    Returns:
        聊天响应 / Chat response
    """
    try:
        claude_service = get_claude_service()
        
        # 获取或生成会话ID / Get or generate session ID
        session_id = None
        if request.session_id:
            session_id = request.session_id
        elif request.context and 'session_id' in request.context:
            session_id = request.context['session_id']
        else:
            session_id = str(uuid.uuid4())
            
        logger.info(f"Chat API: Using session_id = {session_id}")
        
        # 🔥 准备上下文，包括简历向量查询 / Prepare context including resume vector query
        context = request.context or {}
        
        # 🔥 README步骤4：基于简历向量查询匹配职位 / README step 4: Query matching jobs based on resume vector
        if http_request and hasattr(http_request, 'app'):
            db_connections = http_request.app.state.db_connections
            if 'jobs_collection' in db_connections and 'resumes_collection' in db_connections and 'openai_client' in db_connections:
                jobs_collection = db_connections['jobs_collection']
                resumes_collection = db_connections['resumes_collection']
                openai_client = db_connections['openai_client']
                
                try:
                    # 🔥 检查是否有简历向量可用于智能匹配 / Check if resume vector is available for smart matching
                    user_id = context.get('session_id', session_id)  # 使用session_id作为用户标识
                    resume_vector = None
                    resume_analysis = None
                    
                    # 尝试获取用户最新的简历向量 / Try to get user's latest resume vector
                    try:
                        user_resumes = resumes_collection.query(
                            query_embeddings=[[0.0] * 1536],  # 虚拟查询获取用户简历
                            n_results=10,
                            where={"user_id": user_id},
                            include=['embeddings', 'metadatas']  # 🔥 关键修复：明确包含embeddings
                        )
                        
                        if (user_resumes.get('embeddings') and 
                            len(user_resumes['embeddings']) > 0 and 
                            user_resumes['embeddings'][0] is not None and 
                            len(user_resumes['embeddings'][0]) > 0):
                            # 使用最新简历向量 / Use latest resume vector
                            resume_vector = user_resumes['embeddings'][0][0]  # 最新的简历向量
                            resume_metadata = user_resumes['metadatas'][0][0]
                            
                            # 重建简历分析数据 / Rebuild resume analysis data
                            import json
                            resume_analysis = {
                                "skills": json.loads(resume_metadata.get('skills', '[]')),
                                "experience_years": resume_metadata.get('experience_years', 0),
                                "location": resume_metadata.get('location', ''),
                                "education_level": resume_metadata.get('education_level', ''),
                                "languages": json.loads(resume_metadata.get('languages', '[]')),
                                "summary": resume_metadata.get('summary', '')
                            }
                            
                            logger.info(f"💼 Using user resume vector for personalized job matching: {user_id}")
                    except Exception as e:
                        logger.info(f"No user resume found, using general query: {e}")
                    
                    # 🔥 智能职位查询：优先使用简历向量，否则使用通用查询 / Smart job query: prefer resume vector, fallback to general query
                    if resume_vector is not None:
                        # 基于简历向量的个性化匹配 / Personalized matching based on resume vector
                        job_results = jobs_collection.query(
                            query_embeddings=[resume_vector],
                            n_results=25  # README要求：返回25个职位
                        )
                        match_type = "personalized"
                    else:
                        # 通用职位查询（回退方案）/ General job query (fallback)
                        from ..database.connection import get_text_embedding
                        query_text = "software engineer developer germany"
                        query_embedding = get_text_embedding(openai_client, query_text)
                        
                        job_results = jobs_collection.query(
                            query_embeddings=[query_embedding],
                            n_results=25
                        )
                        match_type = "general"
                    
                    # 构建职位列表 / Build job list
                    if job_results['metadatas']:
                        jobs = []
                        for metadata in job_results['metadatas'][0]:
                            try:
                                job_data = {
                                    "id": metadata.get('id', ''),
                                    "title": metadata.get('title', ''),
                                    "company_name": metadata.get('company_name', ''),
                                    "location": metadata.get('location', ''),
                                    "description": metadata.get('description', ''),
                                    "url": metadata.get('url', ''),
                                    "job_type": metadata.get('job_type', '未知')
                                }
                                jobs.append(job_data)
                            except:
                                continue
                        
                        if jobs:
                            context['job_postings'] = jobs
                            context['match_type'] = match_type
                            context['resume_analysis'] = resume_analysis  # 传递简历分析数据
                            logger.info(f"💼 Enhanced message with job postings context for session {session_id}: {len(jobs)} jobs ({match_type} matching)")
                            
                except Exception as e:
                    logger.warning(f"Failed to fetch job data: {e}")
        
        # 收集完整响应 / Collect complete response
        complete_response = ""
        tool_results = []
        
        async for event in claude_service.chat_stream_unified(
            request.message, 
            context, 
            session_id
        ):
            if event.get("type") == "text_delta":
                complete_response += event.get("content", "")
            elif event.get("type") == "tool_execution_complete":
                tool_results.append({
                    "tool_name": event.get("tool_name"),
                    "result": event.get("result")
                })
        
        return ChatResponse(
            response=complete_response,
            message_type="text",
            data={
                "session_id": session_id,
                "tool_results": tool_results,
                **(context or {})
            }
        )
        
    except Exception as e:
        logger.error(f"Chat message failed: {e}")
        raise HTTPException(status_code=500, detail=f"聊天失败: {str(e)}")


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """
    流式聊天 / Streaming chat
    兼容旧接口，重定向到统一接口 / Backward compatibility, redirect to unified interface
    
    Args:
        request: 聊天请求 / Chat request
        
    Returns:
        流式聊天响应 / Streaming chat response
    """
    try:
        # 重定向到统一接口 / Redirect to unified interface
        return await unified_chat(request)
        
    except Exception as e:
        logger.error(f"Streaming chat failed: {e}")
        raise HTTPException(status_code=500, detail=f"流式聊天失败: {str(e)}")


# 向后兼容的独立端点 / Backward compatibility standalone endpoints
@router.post("/analyze-resume")
async def analyze_resume_standalone(
    user_id: str,
    resume_content: str,
    filename: str,
    request: Request
):
    """
    独立简历分析端点 / Standalone resume analysis endpoint
    向后兼容，建议使用统一聊天接口 / Backward compatibility, recommend using unified chat interface
    """
    try:
        logger.warning("Using deprecated standalone resume analysis endpoint. Please use unified chat interface.")
        
        claude_service = get_claude_service()
        
        # 构建聊天请求 / Build chat request
        message = f"请分析我的简历文件：{filename}。请提供详细的分析和改进建议。"
        context = {
            "file_content": resume_content,
            "filename": filename,
            "resume_uploaded": True,
            "user_id": user_id
        }
        
        # 使用统一服务 / Use unified service
        session_id = str(uuid.uuid4())
        analysis_result = None
        job_matches = []
        
        async for event in claude_service.chat_stream_unified(message, context, session_id):
            if event.get("type") == "tool_execution_complete":
                tool_name = event.get("tool_name")
                result = event.get("result")
                
                if tool_name == "analyze_resume":
                    analysis_result = result
                elif tool_name == "match_jobs_with_resume":
                    job_matches = result.get('matches', [])
        
        if not analysis_result:
            raise HTTPException(status_code=400, detail="简历分析失败")
        
        return {
            "analysis": analysis_result,
            "job_matches": job_matches,
            "message_type": "resume_analysis",
            "total_matches": len(job_matches),
            "session_id": session_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Standalone resume analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"简历分析失败: {str(e)}")


@router.get("/skill-heatmap/{job_title}")
async def generate_skill_heatmap_standalone(job_title: str):
    """
    独立技能热点图端点 / Standalone skill heatmap endpoint
    向后兼容，建议使用统一聊天接口 / Backward compatibility, recommend using unified chat interface
    """
    try:
        logger.warning("Using deprecated standalone skill heatmap endpoint. Please use unified chat interface.")
        
        claude_service = get_claude_service()
        
        # 直接调用工具 / Direct tool call
        heatmap_data = await claude_service._tool_generate_skill_heatmap(job_title)
        
        return {
            "heatmap_data": heatmap_data,
            "message_type": "skill_heatmap",
            "job_title": job_title
        }
        
    except Exception as e:
        logger.error(f"Standalone skill heatmap generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"技能热点图生成失败: {str(e)}")


@router.get("/market-insights")
async def get_market_insights_standalone(query: str):
    """
    独立市场洞察端点 / Standalone market insights endpoint
    向后兼容，建议使用统一聊天接口 / Backward compatibility, recommend using unified chat interface
    """
    try:
        logger.warning("Using deprecated standalone market insights endpoint. Please use unified chat interface.")
        
        claude_service = get_claude_service()
        
        # 直接调用工具 / Direct tool call
        insights_data = await claude_service._tool_get_market_insights(query)
        
        return {
            "insights": insights_data.get("content", ""),
            "message_type": "market_insights",
            "query": query
        }
        
    except Exception as e:
        logger.error(f"Standalone market insights failed: {e}")
        raise HTTPException(status_code=500, detail=f"市场洞察失败: {str(e)}")


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
        # 目前返回空历史，未来可以与SQLite集成 / Currently return empty history, can integrate with SQLite in future
        
        return {
            "messages": [],
            "total_count": 0,
            "user_id": user_id,
            "sessions": []
        }
        
    except Exception as e:
        logger.error(f"Failed to get chat history: {e}")
        raise HTTPException(status_code=500, detail=f"获取聊天历史失败: {str(e)}")


@router.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """
    清除会话状态 / Clear session state
    
    Args:
        session_id: 会话ID / Session ID
        
    Returns:
        清除结果 / Clear result
    """
    try:
        claude_service = get_claude_service()
        
        # 清除会话状态 / Clear session state
        if session_id in claude_service.session_state:
            del claude_service.session_state[session_id]
            
        return {
            "success": True,
            "message": f"Session {session_id} cleared",
            "session_id": session_id
        }
        
    except Exception as e:
        logger.error(f"Failed to clear session: {e}")
        raise HTTPException(status_code=500, detail=f"清除会话失败: {str(e)}")


@router.get("/sessions")
async def list_sessions():
    """
    列出所有活跃会话 / List all active sessions
    
    Returns:
        会话列表 / Session list
    """
    try:
        claude_service = get_claude_service()
        
        sessions = []
        for session_id, session_data in claude_service.session_state.items():
            sessions.append({
                "session_id": session_id,
                "messages_count": len(session_data.get("messages", [])),
                "has_resume_analysis": session_data.get("resume_analysis") is not None,
                "job_postings_count": len(session_data.get("job_postings", []))
            })
        
        return {
            "sessions": sessions,
            "total_sessions": len(sessions)
        }
        
    except Exception as e:
        logger.error(f"Failed to list sessions: {e}")
        raise HTTPException(status_code=500, detail=f"获取会话列表失败: {str(e)}") 


@router.get("/token-usage")
async def get_token_usage(session_id: Optional[str] = None):
    """
    获取token使用统计 / Get token usage statistics
    
    Args:
        session_id: 可选的会话ID / Optional session ID
        
    Returns:
        Token使用统计信息 / Token usage statistics
    """
    try:
        claude_service = get_claude_service()
        usage_stats = await claude_service.get_token_usage_stats(session_id)
        
        return {
            "status": "success",
            "data": usage_stats,
            "message": "Token usage statistics retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to get token usage: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve token usage statistics: {str(e)}"
        )


@router.post("/budget-alert")
async def check_budget_alert(daily_budget: float = 5.0):
    """
    检查预算警告 / Check budget alerts
    
    Args:
        daily_budget: 每日预算限制 (USD) / Daily budget limit in USD
        
    Returns:
        预算状态信息 / Budget status information
    """
    try:
        claude_service = get_claude_service()
        budget_status = claude_service.token_tracker.check_budget_alert(daily_budget)
        
        return {
            "status": "success",
            "data": budget_status,
            "message": f"Budget status: {budget_status['alert_level']}"
        }
        
    except Exception as e:
        logger.error(f"Failed to check budget: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check budget status: {str(e)}"
        ) 