"""
文件上传API / File upload API
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Request
from typing import Optional
import logging
import os
import uuid
import aiofiles
import base64

from ..models.user import ResumeUploadRequest
from ..services.claude_service import ClaudeService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/resume")
async def upload_resume(
    request: Request,
    file: UploadFile = File(...),
    user_id: str = Form(...)
):
    """
    上传简历文件 / Upload resume file
    
    Args:
        file: 上传的文件 / Uploaded file
        user_id: 用户ID / User ID
        
    Returns:
        上传结果和文件信息 / Upload result and file info
    """
    try:
        # 验证文件类型 / Validate file type
        allowed_types = ['application/pdf', 'text/plain', 'application/msword', 
                        'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
        
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400, 
                detail=f"不支持的文件类型: {file.content_type}。支持的类型: PDF, TXT, DOC, DOCX"
            )
        
        # 验证文件大小 / Validate file size (32MB limit for Claude PDF support)
        max_size = 32 * 1024 * 1024  # 32MB - Claude PDF支持的最大大小
        file_content = await file.read()
        
        if len(file_content) > max_size:
            raise HTTPException(
                status_code=400,
                detail="文件大小超过32MB限制"
            )
        
        # 生成唯一文件名 / Generate unique filename
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = f"uploads/{unique_filename}"
        
        # 确保上传目录存在 / Ensure upload directory exists
        os.makedirs("uploads", exist_ok=True)
        
        # 保存文件 / Save file
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(file_content)
        
        # 🔥 新功能：为Claude 4准备文档数据 / NEW: Prepare document data for Claude 4
        document_data = await _prepare_document_for_claude(file_path, file.content_type, file_content)
        
        # 🔥 README步骤2-3：Claude 4分析简历并向量化存储 / README steps 2-3: Claude 4 analysis and vectorization
        resume_id = None
        vector_stored = False
        try:
            resume_id = await _analyze_and_store_resume_vector(user_id, unique_filename, document_data, request)
            vector_stored = True
            logger.info(f"✅ Resume vector stored successfully: {resume_id}")
        except Exception as e:
            logger.warning(f"⚠️ 简历向量化存储失败，但文件上传成功: {e}")
        
        logger.info(f"Resume uploaded successfully: {file.filename} for user {user_id}")
        
        return {
            "message": "简历上传成功",
            "filename": file.filename,
            "unique_filename": unique_filename,
            "file_path": file_path,
            "content_type": file.content_type,
            "size": len(file_content),
            "user_id": user_id,
            # 🔥 关键：返回Claude 4可以直接使用的文档数据 / CRITICAL: Return document data for Claude 4
            "document_data": document_data,
            "claude_native_support": True,  # 标识支持Claude原生处理
            "vector_stored": vector_stored,  # 标识是否已向量化存储
            "resume_id": resume_id  # 简历向量ID，用于后续匹配
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Resume upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")


async def _prepare_document_for_claude(file_path: str, content_type: str, file_content: bytes) -> dict:
    """
    🔥 新功能：为Claude 4准备文档数据 / NEW: Prepare document data for Claude 4
    
    Args:
        file_path: 文件路径 / File path
        content_type: 文件类型 / Content type
        file_content: 文件内容字节 / File content bytes
        
    Returns:
        Claude 4可以直接使用的文档数据 / Document data that Claude 4 can use directly
    """
    try:
        if content_type == 'application/pdf':
            # 🔥 PDF文件：使用Claude 4原生PDF支持 / PDF: Use Claude 4 native PDF support
            # 将PDF文件编码为base64供Claude处理 / Encode PDF as base64 for Claude
            base64_content = base64.b64encode(file_content).decode('utf-8')
            
            return {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": base64_content
                },
                "claude_format": "native_pdf"  # 标识使用Claude原生PDF处理
            }
            
        elif content_type == 'text/plain':
            # 文本文件：直接读取内容 / Text file: read content directly
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                text_content = await f.read()
            
            return {
                "type": "text",
                "content": text_content,
                "claude_format": "text"
            }
                
        elif content_type in ['application/msword', 
                             'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
            # Word文档：提取文本内容（Claude 4暂不支持原生Word处理） / Word: extract text (Claude 4 doesn't support native Word yet)
            try:
                from docx import Document
                doc = Document(file_path)
                text_content = ""
                for paragraph in doc.paragraphs:
                    text_content += paragraph.text + "\n"
                
                return {
                    "type": "text",
                    "content": text_content,
                    "claude_format": "extracted_text",
                    "original_format": "docx"
                }
            except ImportError:
                raise HTTPException(status_code=500, detail="Word文档处理库未安装")
        
        else:
            raise HTTPException(status_code=400, detail="不支持的文件类型")
            
    except Exception as e:
        logger.error(f"Document preparation for Claude failed: {e}")
        # 回退到文本提取 / Fallback to text extraction
        try:
            return await _fallback_text_extraction(file_path, content_type)
        except:
            raise HTTPException(status_code=500, detail=f"文档处理失败: {str(e)}")


async def _analyze_and_store_resume_vector(user_id: str, filename: str, document_data: dict, request) -> str:
    """
    🔥 README步骤2-3：使用Claude 4分析简历并向量化存储 / README steps 2-3: Analyze resume with Claude 4 and store vector
    """
    import uuid
    import json
    import time
    from datetime import datetime
    from ..database.connection import get_text_embedding
    
    try:
        # 获取数据库连接 / Get database connections
        db_connections = request.app.state.db_connections
        resumes_collection = db_connections['resumes_collection']
        openai_client = db_connections['openai_client']
        claude_service = request.app.state.claude_service
        
        # 🔥 Claude 4简历分析 / Claude 4 resume analysis
        resume_analysis_prompt = """请分析这份简历，提取以下结构化信息并以JSON格式返回：

{
  "skills": ["技能1", "技能2", "技能3"],
  "experience_years": 3,
  "location": "Berlin",
  "education_level": "Bachelor",
  "languages": ["German", "English", "Chinese"],
  "summary": "简历概述"
}

重点关注：
1. 技术技能和专业技能
2. 工作经验年限
3. 地理位置偏好
4. 教育水平
5. 语言能力

请返回标准JSON格式。"""
        
        # 使用Claude 4分析简历 / Use Claude 4 to analyze resume
        analysis_text = ""
        async for chunk in claude_service.chat_stream_unified(
            resume_analysis_prompt,
            context={"uploaded_document": document_data}
        ):
            if chunk.get("type") == "text":
                analysis_text += chunk.get("content", "")
        
        # 解析分析结果 / Parse analysis results
        try:
            # 尝试提取JSON / Try to extract JSON
            import re
            json_match = re.search(r'\{.*\}', analysis_text, re.DOTALL)
            if json_match:
                resume_analysis = json.loads(json_match.group())
            else:
                raise ValueError("No JSON found in Claude response")
        except (json.JSONDecodeError, ValueError):
            # 如果解析失败，使用默认值 / Use default values if parsing fails
            resume_analysis = {
                "skills": ["General"],
                "experience_years": 0,
                "location": "Germany",
                "education_level": "Unknown",
                "languages": ["German"],
                "summary": "简历分析处理中"
            }
        
        # 🔥 构建向量化文本 / Build vectorization text
        vectorization_text = _build_resume_vectorization_text(resume_analysis)
        
        # 🔥 生成向量 / Generate vector
        resume_vector = get_text_embedding(openai_client, vectorization_text)
        
        # 🔥 生成唯一ID / Generate unique ID
        resume_id = f"resume_{user_id}_{int(time.time())}"
        
        # 🔥 存储到Chroma / Store in Chroma
        resumes_collection.add(
            embeddings=[resume_vector],
            documents=[vectorization_text],
            metadatas=[{
                "user_id": user_id,
                "resume_id": resume_id,
                "filename": filename,
                "skills": json.dumps(resume_analysis.get("skills", [])),
                "experience_years": resume_analysis.get("experience_years", 0),
                "location": resume_analysis.get("location", ""),
                "education_level": resume_analysis.get("education_level", ""),
                "languages": json.dumps(resume_analysis.get("languages", [])),
                "summary": resume_analysis.get("summary", ""),
                "created_at": datetime.now().isoformat(),
                "analysis_method": "claude4_native"
            }],
            ids=[resume_id]
        )
        
        logger.info(f"📝 Resume analysis and vector storage completed for user {user_id}")
        return resume_id
        
    except Exception as e:
        logger.error(f"❌ Resume analysis and vector storage failed: {e}")
        raise


def _build_resume_vectorization_text(resume_analysis: dict) -> str:
    """
    🔥 构建用于向量化的简历文本 / Build resume text for vectorization
    按照README要求的权重：技能>经验>地点>语言>学历
    """
    components = []
    
    # 技能（最高权重，重复3次增强重要性）/ Skills (highest weight, repeat 3 times)
    skills = resume_analysis.get("skills", [])
    if skills:
        skills_text = " ".join(skills)
        components.extend([f"Skills: {skills_text}"] * 3)
    
    # 经验（高权重，重复2次）/ Experience (high weight, repeat 2 times)
    experience_years = resume_analysis.get("experience_years", 0)
    experience_text = f"Experience: {experience_years} years"
    components.extend([experience_text] * 2)
    
    # 地点（中等权重）/ Location (medium weight)
    location = resume_analysis.get("location", "")
    if location:
        components.append(f"Location: {location}")
    
    # 语言（中等权重）/ Languages (medium weight)
    languages = resume_analysis.get("languages", [])
    if languages:
        languages_text = " ".join(languages)
        components.append(f"Languages: {languages_text}")
    
    # 教育（较低权重）/ Education (lower weight)
    education = resume_analysis.get("education_level", "")
    if education:
        components.append(f"Education: {education}")
    
    # 摘要 / Summary
    summary = resume_analysis.get("summary", "")
    if summary:
        components.append(f"Summary: {summary}")
    
    return " | ".join(components)


async def _fallback_text_extraction(file_path: str, content_type: str) -> dict:
    """
    回退文本提取方法 / Fallback text extraction method
    """
    try:
        if content_type == 'application/pdf':
            # PDF回退方案 / PDF fallback
            try:
                import PyPDF2
                with open(file_path, 'rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    text = ""
                    for page in pdf_reader.pages:
                        text += page.extract_text()
                    
                    return {
                        "type": "text",
                        "content": text,
                        "claude_format": "extracted_text",
                        "original_format": "pdf"
                    }
            except ImportError:
                raise HTTPException(status_code=500, detail="PDF处理库未安装")
        
        # 其他情况返回空内容 / Return empty content for other cases
        return {
            "type": "text",
            "content": "",
            "claude_format": "empty",
            "error": "无法处理此文件类型"
        }
        
    except Exception as e:
        logger.error(f"Fallback text extraction failed: {e}")
        return {
            "type": "text",
            "content": "",
            "claude_format": "empty",
            "error": str(e)
        }


@router.delete("/resume/{filename}")
async def delete_resume(filename: str, user_id: str):
    """
    删除简历文件 / Delete resume file
    
    Args:
        filename: 文件名 / Filename
        user_id: 用户ID / User ID
        
    Returns:
        删除结果 / Deletion result
    """
    try:
        file_path = f"uploads/{filename}"
        
        # 检查文件是否存在 / Check if file exists
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 删除文件 / Delete file
        os.remove(file_path)
        
        # TODO: 从数据库删除相关记录 / Delete related records from database
        
        logger.info(f"Resume deleted: {filename} for user {user_id}")
        
        return {"message": "文件删除成功", "filename": filename}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Resume deletion failed: {e}")
        raise HTTPException(status_code=500, detail=f"文件删除失败: {str(e)}")


@router.get("/resume/{filename}")
async def get_resume_info(filename: str, user_id: str):
    """
    获取简历文件信息 / Get resume file info
    
    Args:
        filename: 文件名 / Filename
        user_id: 用户ID / User ID
        
    Returns:
        文件信息 / File information
    """
    try:
        file_path = f"uploads/{filename}"
        
        # 检查文件是否存在 / Check if file exists
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 获取文件信息 / Get file info
        file_stat = os.stat(file_path)
        
        return {
            "filename": filename,
            "file_path": file_path,
            "size": file_stat.st_size,
            "created_time": file_stat.st_ctime,
            "modified_time": file_stat.st_mtime
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get resume info failed: {e}")
        raise HTTPException(status_code=500, detail=f"获取文件信息失败: {str(e)}") 


@router.get("/health")
async def health_check():
    """
    健康检查端点 / Health check endpoint
    """
    return {"status": "ok", "message": "File upload service is running"} 