"""
文件上传API / File upload API
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Optional
import logging
import os
import uuid
import aiofiles

from ..models.user import ResumeUploadRequest
from ..services.claude_service import ClaudeService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/resume")
async def upload_resume(
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
        
        # 验证文件大小 / Validate file size (5MB limit)
        max_size = 5 * 1024 * 1024  # 5MB
        file_content = await file.read()
        
        if len(file_content) > max_size:
            raise HTTPException(
                status_code=400,
                detail="文件大小超过5MB限制"
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
        
        # 提取文本内容 / Extract text content
        text_content = await _extract_text_from_file(file_path, file.content_type)
        
        logger.info(f"Resume uploaded successfully: {file.filename} for user {user_id}")
        
        return {
            "message": "简历上传成功",
            "filename": file.filename,
            "unique_filename": unique_filename,
            "file_path": file_path,
            "content_type": file.content_type,
            "size": len(file_content),
            "text_content": text_content[:500] + "..." if len(text_content) > 500 else text_content,
            "user_id": user_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Resume upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")


async def _extract_text_from_file(file_path: str, content_type: str) -> str:
    """
    从文件中提取文本内容 / Extract text content from file
    
    Args:
        file_path: 文件路径 / File path
        content_type: 文件类型 / Content type
        
    Returns:
        提取的文本内容 / Extracted text content
    """
    try:
        if content_type == 'text/plain':
            # 处理纯文本文件 / Handle plain text files
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                return await f.read()
                
        elif content_type == 'application/pdf':
            # 处理PDF文件 / Handle PDF files
            try:
                import PyPDF2
                with open(file_path, 'rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    text = ""
                    for page in pdf_reader.pages:
                        text += page.extract_text()
                    return text
            except ImportError:
                raise HTTPException(status_code=500, detail="PDF处理库未安装")
                
        elif content_type in ['application/msword', 
                             'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
            # 处理Word文档 / Handle Word documents
            try:
                from docx import Document
                doc = Document(file_path)
                text = ""
                for paragraph in doc.paragraphs:
                    text += paragraph.text + "\n"
                return text
            except ImportError:
                raise HTTPException(status_code=500, detail="Word文档处理库未安装")
        
        else:
            raise HTTPException(status_code=400, detail="不支持的文件类型")
            
    except Exception as e:
        logger.error(f"Text extraction failed: {e}")
        # 如果文本提取失败，返回空字符串而不是抛出异常 / Return empty string if extraction fails
        return ""


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
            "modified_time": file_stat.st_mtime,
            "user_id": user_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get resume info failed: {e}")
        raise HTTPException(status_code=500, detail=f"获取文件信息失败: {str(e)}") 