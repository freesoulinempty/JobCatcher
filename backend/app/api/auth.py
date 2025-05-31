"""
用户认证API端点 / User authentication API endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
from loguru import logger

from ..services.auth_service import auth_service


router = APIRouter(prefix="/auth", tags=["authentication"])


class LoginResponse(BaseModel):
    """登录响应模型 / Login response model"""
    authorization_url: str
    state: str


class CallbackRequest(BaseModel):
    """OAuth回调请求模型 / OAuth callback request model"""
    code: str
    state: str


class UserProfile(BaseModel):
    """用户资料模型 / User profile model"""
    id: str
    email: str
    name: str
    picture: str
    google_id: str
    created_at: str
    updated_at: str
    is_active: bool


# 依赖函数：获取当前用户 / Dependency function: get current user
async def get_current_user(request: Request) -> Dict[str, Any]:
    """
    获取当前认证用户 / Get current authenticated user
    
    Args:
        request: HTTP请求对象 / HTTP request object
        
    Returns:
        当前用户信息 / Current user info
        
    Raises:
        HTTPException: 如果用户未认证 / If user is not authenticated
    """
    session_id = request.cookies.get("session_id")
    
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user_info = await auth_service.verify_session(session_id)
    
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    return user_info


# 可选依赖函数：获取当前用户（可选） / Optional dependency function: get current user (optional)
async def get_current_user_optional(request: Request) -> Optional[Dict[str, Any]]:
    """
    获取当前认证用户（可选，不抛出异常） / Get current authenticated user (optional, no exception)
    
    Args:
        request: HTTP请求对象 / HTTP request object
        
    Returns:
        当前用户信息或None / Current user info or None
    """
    try:
        return await get_current_user(request)
    except HTTPException:
        return None


@router.get("/login", response_model=LoginResponse)
async def login():
    """
    获取Google OAuth登录URL / Get Google OAuth login URL
    
    Returns:
        包含授权URL和状态的响应 / Response with authorization URL and state
    """
    try:
        authorization_url = auth_service.get_authorization_url()
        
        # 从URL中提取state参数 / Extract state parameter from URL
        import urllib.parse as urlparse
        parsed_url = urlparse.urlparse(authorization_url)
        query_params = urlparse.parse_qs(parsed_url.query)
        state = query_params.get('state', [''])[0]
        
        return LoginResponse(
            authorization_url=authorization_url,
            state=state
        )
        
    except Exception as e:
        logger.error(f"Login endpoint failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate login URL")


@router.post("/callback")
async def oauth_callback(callback_data: CallbackRequest, response: Response):
    """
    处理Google OAuth回调 / Handle Google OAuth callback
    
    Args:
        callback_data: OAuth回调数据 / OAuth callback data
        response: HTTP响应对象 / HTTP response object
        
    Returns:
        用户信息和会话数据 / User info and session data
    """
    try:
        result = await auth_service.handle_oauth_callback(
            authorization_code=callback_data.code,
            state=callback_data.state
        )
        
        if not result.get('success'):
            raise HTTPException(
                status_code=400, 
                detail=result.get('error', 'OAuth callback failed')
            )
        
        # 设置会话Cookie / Set session cookie
        session_id = result['session']['session_id']
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=86400 * 7  # 7天 / 7 days
        )
        
        return {
            "message": "Login successful",
            "user": result['user'],
            "session_id": session_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth callback failed: {e}")
        raise HTTPException(status_code=500, detail="OAuth callback processing failed")


@router.get("/profile", response_model=UserProfile)
async def get_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    获取当前用户资料 / Get current user profile
    
    Args:
        current_user: 当前用户信息 / Current user info
        
    Returns:
        用户资料 / User profile
    """
    try:
        profile = await auth_service.get_user_profile(current_user['user_id'])
        
        if not profile:
            raise HTTPException(status_code=404, detail="User profile not found")
        
        return UserProfile(**profile)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get profile failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user profile")


@router.post("/logout")
async def logout(response: Response, current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    用户登出 / User logout
    
    Args:
        response: HTTP响应对象 / HTTP response object
        current_user: 当前用户信息 / Current user info
        
    Returns:
        登出结果 / Logout result
    """
    try:
        success = await auth_service.logout(current_user['session_id'])
        
        if success:
            # 清除会话Cookie / Clear session cookie
            response.delete_cookie(key="session_id")
            return {"message": "Logout successful"}
        else:
            raise HTTPException(status_code=400, detail="Logout failed")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Logout failed: {e}")
        raise HTTPException(status_code=500, detail="Logout processing failed")


@router.get("/verify")
async def verify_session(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    验证当前会话 / Verify current session
    
    Args:
        current_user: 当前用户信息 / Current user info
        
    Returns:
        会话验证结果 / Session verification result
    """
    return {
        "valid": True,
        "user": {
            "user_id": current_user['user_id'],
            "email": current_user['email'],
            "name": current_user['name'],
            "picture": current_user['picture']
        }
    } 