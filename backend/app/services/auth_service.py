"""
Google OAuth 2.0 认证服务 / Google OAuth 2.0 authentication service
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from google.auth.transport.requests import Request
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
import sqlite3
from loguru import logger

from ..core.config import settings
from ..database.connection import get_sqlite_db


class GoogleAuthService:
    """Google OAuth 2.0 认证服务类 / Google OAuth 2.0 authentication service class"""
    
    def __init__(self):
        self.client_id = settings.google_client_id
        self.client_secret = settings.google_client_secret
        self.redirect_uri = settings.google_redirect_uri
        
        # OAuth 2.0 流程配置 / OAuth 2.0 flow configuration
        self.flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.redirect_uri]
                }
            },
            scopes=[
                'openid',
                'https://www.googleapis.com/auth/userinfo.email',
                'https://www.googleapis.com/auth/userinfo.profile'
            ]
        )
        self.flow.redirect_uri = self.redirect_uri
    
    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """
        获取Google OAuth授权URL / Get Google OAuth authorization URL
        
        Args:
            state: 状态参数，用于防止CSRF攻击 / State parameter for CSRF protection
            
        Returns:
            授权URL / Authorization URL
        """
        try:
            if not state:
                state = str(uuid.uuid4())
            
            authorization_url, _ = self.flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                state=state
            )
            
            logger.info(f"Generated Google OAuth authorization URL with state: {state}")
            return authorization_url
            
        except Exception as e:
            logger.error(f"Failed to generate authorization URL: {e}")
            raise
    
    async def handle_oauth_callback(self, authorization_code: str, state: str) -> Dict[str, Any]:
        """
        处理OAuth回调 / Handle OAuth callback
        
        Args:
            authorization_code: 授权码 / Authorization code
            state: 状态参数 / State parameter
            
        Returns:
            用户信息和会话数据 / User info and session data
        """
        try:
            # 创建新的flow实例避免scope验证问题 / Create new flow instance to avoid scope validation issues
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": [self.redirect_uri]
                    }
                },
                scopes=[
                    'openid',
                    'https://www.googleapis.com/auth/userinfo.email',
                    'https://www.googleapis.com/auth/userinfo.profile'
                ]
            )
            flow.redirect_uri = self.redirect_uri
            
            # 获取访问令牌 / Get access token
            flow.fetch_token(code=authorization_code)
            
            # 验证ID令牌 / Verify ID token
            credentials = flow.credentials
            id_info = id_token.verify_oauth2_token(
                credentials.id_token,
                Request(),
                self.client_id
            )
            
            # 提取用户信息 / Extract user information
            user_info = {
                'google_id': id_info['sub'],
                'email': id_info['email'],
                'name': id_info['name'],
                'picture': id_info.get('picture', ''),
                'email_verified': id_info.get('email_verified', False)
            }
            
            # 创建或更新用户 / Create or update user
            user_id = await self._create_or_update_user(user_info)
            
            # 创建会话 / Create session
            session_data = await self._create_user_session(
                user_id=user_id,
                access_token=credentials.token,
                refresh_token=credentials.refresh_token,
                expires_at=credentials.expiry
            )
            
            logger.info(f"OAuth callback handled successfully for user: {user_info['email']}")
            
            return {
                'user': user_info,
                'session': session_data,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"OAuth callback handling failed: {e}")
            return {
                'error': str(e),
                'success': False
            }
    
    async def _create_or_update_user(self, user_info: Dict[str, Any]) -> str:
        """
        创建或更新用户 / Create or update user
        
        Args:
            user_info: 用户信息 / User information
            
        Returns:
            用户ID / User ID
        """
        conn = get_sqlite_db()
        try:
            # 检查用户是否存在 / Check if user exists
            cursor = conn.execute(
                "SELECT id FROM users WHERE google_id = ? OR email = ?",
                (user_info['google_id'], user_info['email'])
            )
            existing_user = cursor.fetchone()
            
            if existing_user:
                # 更新现有用户 / Update existing user
                user_id = existing_user[0]
                conn.execute("""
                    UPDATE users 
                    SET name = ?, picture = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (user_info['name'], user_info['picture'], user_id))
                logger.info(f"Updated existing user: {user_info['email']}")
            else:
                # 创建新用户 / Create new user
                user_id = str(uuid.uuid4())
                conn.execute("""
                    INSERT INTO users (id, email, name, picture, google_id, created_at, updated_at, is_active)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, TRUE)
                """, (
                    user_id,
                    user_info['email'],
                    user_info['name'],
                    user_info['picture'],
                    user_info['google_id']
                ))
                logger.info(f"Created new user: {user_info['email']}")
            
            conn.commit()
            return user_id
            
        finally:
            conn.close()
    
    async def _create_user_session(self, user_id: str, access_token: str, 
                                 refresh_token: Optional[str], expires_at: datetime) -> Dict[str, Any]:
        """
        创建用户会话 / Create user session
        
        Args:
            user_id: 用户ID / User ID
            access_token: 访问令牌 / Access token
            refresh_token: 刷新令牌 / Refresh token
            expires_at: 过期时间 / Expiration time
            
        Returns:
            会话数据 / Session data
        """
        conn = get_sqlite_db()
        try:
            session_id = str(uuid.uuid4())
            
            # 删除旧会话 / Delete old sessions
            conn.execute("DELETE FROM user_sessions WHERE user_id = ?", (user_id,))
            
            # 创建新会话 / Create new session
            conn.execute("""
                INSERT INTO user_sessions (session_id, user_id, access_token, refresh_token, expires_at, created_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (session_id, user_id, access_token, refresh_token, expires_at))
            
            conn.commit()
            
            return {
                'session_id': session_id,
                'user_id': user_id,
                'expires_at': expires_at.isoformat() if expires_at else None
            }
            
        finally:
            conn.close()
    
    async def verify_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        验证用户会话 / Verify user session
        
        Args:
            session_id: 会话ID / Session ID
            
        Returns:
            用户信息或None / User info or None
        """
        conn = get_sqlite_db()
        try:
            cursor = conn.execute("""
                SELECT s.user_id, s.expires_at, u.email, u.name, u.picture, u.is_active
                FROM user_sessions s
                JOIN users u ON s.user_id = u.id
                WHERE s.session_id = ?
            """, (session_id,))
            
            result = cursor.fetchone()
            if not result:
                return None
            
            user_id, expires_at, email, name, picture, is_active = result
            
            # 检查会话是否过期 / Check if session is expired
            if expires_at:
                expires_datetime = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                if expires_datetime < datetime.now():
                    # 删除过期会话 / Delete expired session
                    conn.execute("DELETE FROM user_sessions WHERE session_id = ?", (session_id,))
                    conn.commit()
                    return None
            
            # 检查用户是否激活 / Check if user is active
            if not is_active:
                return None
            
            return {
                'user_id': user_id,
                'email': email,
                'name': name,
                'picture': picture,
                'session_id': session_id
            }
            
        except Exception as e:
            logger.error(f"Session verification failed: {e}")
            return None
        finally:
            conn.close()
    
    async def logout(self, session_id: str) -> bool:
        """
        用户登出 / User logout
        
        Args:
            session_id: 会话ID / Session ID
            
        Returns:
            是否成功 / Success status
        """
        conn = get_sqlite_db()
        try:
            cursor = conn.execute("DELETE FROM user_sessions WHERE session_id = ?", (session_id,))
            conn.commit()
            
            success = cursor.rowcount > 0
            if success:
                logger.info(f"User logged out successfully: {session_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Logout failed: {e}")
            return False
        finally:
            conn.close()
    
    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        获取用户资料 / Get user profile
        
        Args:
            user_id: 用户ID / User ID
            
        Returns:
            用户资料 / User profile
        """
        conn = get_sqlite_db()
        try:
            cursor = conn.execute("""
                SELECT id, email, name, picture, google_id, created_at, updated_at, is_active
                FROM users WHERE id = ?
            """, (user_id,))
            
            result = cursor.fetchone()
            if not result:
                return None
            
            return {
                'id': result[0],
                'email': result[1],
                'name': result[2],
                'picture': result[3],
                'google_id': result[4],
                'created_at': result[5],
                'updated_at': result[6],
                'is_active': bool(result[7])
            }
            
        except Exception as e:
            logger.error(f"Failed to get user profile: {e}")
            return None
        finally:
            conn.close()


# 全局认证服务实例 / Global authentication service instance
auth_service = GoogleAuthService() 