"""
Supabase认证服务
"""

import logging
import json
import jwt
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import os
from fastapi import HTTPException, status, Request, Response
from supabase import Client
from supabase_client import supabase, SUPABASE_SERVICE_ROLE_KEY
from supabase_models import UserCreate, UserResponse, UserLogin, TokenResponse, UserCreatedResponse

# 配置日志
logger = logging.getLogger(__name__)

class SupabaseAuthService:
    """Supabase认证服务类"""
    
    def __init__(self, supabase_client: Client = None):
        """初始化认证服务"""
        # 配置缺失/无效时不让应用崩溃：页面仍可访问，
        # 认证操作在实际调用时通过 client 属性给出明确错误
        self._client = supabase_client or supabase
        if not self._client:
            logger.warning(
                "Supabase 客户端不可用：请检查 SUPABASE_URL / SUPABASE_KEY 配置"
                "（参考 config/.env.example），注册/登录功能将不可用"
            )

    @property
    def client(self) -> Client:
        """Supabase客户端，未配置时在使用处抛出带配置指引的异常"""
        if not self._client:
            raise ValueError(
                "Supabase客户端未初始化：请检查 SUPABASE_URL / SUPABASE_KEY 配置"
                "（参考 config/.env.example 与 docs/supabase_setup.sql）"
            )
        return self._client
    
    async def register_user(self, user_data: UserCreate) -> dict:
        """注册新用户
        
        Args:
            user_data: 用户注册信息
            
        Returns:
            包含注册结果的字典，包括是否需要邮箱验证等信息
        """
        try:
            # 调用Supabase的注册API - 注意：不需要await
            response = self.client.auth.sign_up({
                "email": user_data.email,
                "password": user_data.password
            })
            
            # 检查响应
            if response and hasattr(response, 'user'):
                user = response.user
                logger.info(f"用户 {user_data.email} 注册成功")
                
                # 检查是否需要邮箱验证
                needs_verification = True
                if user and hasattr(user, 'email_confirmed_at'):
                    needs_verification = user.email_confirmed_at is None
                
                return {
                    "success": True,
                    "needs_email_verification": needs_verification,
                    "user": user
                }
            else:
                logger.error("注册响应无效")
                raise Exception("注册失败：无效的响应")
            
        except Exception as e:
            logger.error(f"注册失败: {str(e)}")
            raise
    
    async def check_user_exists(self, email: str) -> bool:
        """检查用户邮箱是否已注册
        
        Args:
            email: 用户邮箱
            
        Returns:
            bool: 用户是否存在
        """
        import httpx
        from supabase_client import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY

        if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
            raise HTTPException(
                status_code=503,
                detail="Supabase 配置缺失，请检查 .env 中的 SUPABASE_URL 和 SUPABASE_SERVICE_ROLE_KEY"
            )

        last_error = None
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    response = await client.get(
                        f"{SUPABASE_URL}/auth/v1/admin/users",
                        headers={
                            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
                            "apikey": SUPABASE_SERVICE_ROLE_KEY
                        }
                    )

                    if response.status_code == 200:
                        data = response.json()
                        users = data.get("users", [])
                        email_lower = email.lower().strip()
                        for user in users:
                            if user.get("email", "").lower() == email_lower:
                                logger.debug(f"用户 {email} 已存在")
                                return True
                        logger.debug(f"用户 {email} 不存在")
                        return False

                    logger.warning(
                        f"查询用户列表失败(第{attempt + 1}次): "
                        f"{response.status_code}, {response.text[:200]}"
                    )
                    if response.status_code in (401, 403):
                        raise HTTPException(
                            status_code=503,
                            detail="Supabase 密钥无效，请在 Dashboard → Settings → API 更新 .env 中的密钥"
                        )
                    last_error = f"HTTP {response.status_code}"
            except HTTPException:
                raise
            except Exception as e:
                last_error = str(e) or type(e).__name__
                logger.warning(f"检查用户是否存在出错(第{attempt + 1}次): {last_error}")
                if attempt < 2:
                    import asyncio
                    await asyncio.sleep(1.5 * (attempt + 1))
                    continue

        logger.error(f"检查用户是否存在最终失败: {last_error}")
        raise HTTPException(
            status_code=503,
            detail="认证服务暂时不可用，Supabase 可能仍在启动中，请等待 1-2 分钟后重试"
        )
    
    async def login_user(self, login_data: UserLogin) -> TokenResponse:
        """用户登录
        
        Args:
            login_data: 用户登录信息
            
        Returns:
            包含令牌和用户信息的响应
            
        Raises:
            HTTPException: 登录失败时抛出
        """
        try:
            # 调用Supabase Auth API登录用户
            # 注意：sign_in_with_password方法在新版本SDK中不再需要await
            auth_response = self.client.auth.sign_in_with_password({
                "email": login_data.email,
                "password": login_data.password
            })
            
            if not auth_response.user:
                logger.error(f"用户登录失败: {login_data.email}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="登录失败，邮箱或密码错误"
                )
            
            # 转换为响应模型
            user = UserResponse(
                id=auth_response.user.id,
                email=auth_response.user.email,
                username=auth_response.user.user_metadata.get("username"),
                created_at=auth_response.user.created_at
            )
            
            # 构建令牌响应
            token_response = TokenResponse(
                access_token=auth_response.session.access_token,
                expires_in=auth_response.session.expires_in,
                refresh_token=auth_response.session.refresh_token,
                user=user
            )
            
            logger.info(f"用户登录成功: {user.email}")
            return token_response
            
        except Exception as e:
            logger.error(f"用户登录出错: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"登录过程中出错: {str(e)}"
            )
    
    async def logout_user(self) -> bool:
        """用户登出
        
        Returns:
            操作是否成功
        """
        try:
            # 调用Supabase Auth API登出用户
            # 注意：sign_out方法在新版本SDK中不再需要await
            self.client.auth.sign_out()
            
            # 尝试使用直接的HTTP请求进行登出，确保服务端也知道用户已退出
            try:
                import httpx
                # 获取当前会话的JWT token
                session = self.client.auth.get_session()
                if session and session.access_token:
                    url = f"{self.client.supabase_url}/auth/v1/logout"
                    headers = {
                        "apikey": self.client.supabase_key,
                        "Authorization": f"Bearer {session.access_token}"
                    }
                    
                    async with httpx.AsyncClient() as client:
                        http_response = await client.post(url, headers=headers)
                        logger.debug(f"HTTP登出响应: {http_response.status_code}, {http_response.text[:100]}")
            except Exception as http_error:
                logger.warning(f"HTTP登出请求出错: {str(http_error)}")
                
            # 确保清除客户端状态
            try:
                # 显式地使会话过期，清除内存中的状态
                self.client.auth._config.persist_session = False
                self.client.auth._session = None
                self.client.auth._auto_refresh_token = False
                self.client.auth._initialize_auto_refresh_token = False
                
                # 重置客户端状态
                self.client.auth._initialize()
                
                logger.debug("已清除客户端会话状态")
            except Exception as session_error:
                logger.warning(f"清除客户端会话状态出错: {str(session_error)}")
                
            logger.info("用户登出成功")
            return True
        except Exception as e:
            logger.error(f"用户登出出错: {str(e)}")
            return False
    
    async def reset_password(self, email: str, redirect_to: str = None) -> bool:
        """发送密码重置邮件
        
        Args:
            email: 用户邮箱
            redirect_to: 密码重置后的重定向URL
            
        Returns:
            是否成功发送重置邮件
        """
        try:
            # 如果没有指定重定向URL，使用默认的重置页面
            if not redirect_to:
                # 获取当前服务器地址
                import os
                base_url = os.getenv('BASE_URL', 'http://127.0.0.1:8000')
                redirect_to = f"{base_url}/auth/reset-password-page"
            
            logger.debug(f"准备发送密码重置邮件: email={email}, redirect_to={redirect_to}")
            
            # 调用Supabase Auth API发送密码重置邮件
            # 根据 Supabase Python SDK 的文档，正确的方法是 reset_password_for_email
            response = self.client.auth.reset_password_for_email(
                email,
                options={
                    "redirect_to": redirect_to
                }
            )
            
            logger.info(f"已发送密码重置邮件到: {email}，重定向URL: {redirect_to}")
            logger.debug(f"Supabase响应: {response}")
            return True
        except Exception as e:
            logger.error(f"发送密码重置邮件失败: {str(e)}")
            logger.exception("详细错误信息:")
            return False
    
    async def update_password_with_token(self, access_token: str, new_password: str) -> bool:
        """使用重置令牌更新密码
        
        Args:
            access_token: 密码重置访问令牌
            new_password: 新密码
            
        Returns:
            是否成功更新密码
        """
        try:
            # 使用临时客户端，带上access_token
            from supabase import create_client
            from config.settings import SUPABASE_URL, SUPABASE_KEY
            
            logger.debug(f"准备更新密码，token长度: {len(access_token)}")
            
            # 创建临时客户端
            temp_client = create_client(SUPABASE_URL, SUPABASE_KEY)
            
            # 先设置session，使用access_token
            try:
                # 使用 set_session 方法来设置当前会话
                session_response = temp_client.auth.set_session(access_token, access_token)
                logger.debug(f"设置会话成功: {session_response}")
            except Exception as session_error:
                logger.error(f"设置会话失败: {str(session_error)}")
                # 尝试另一种方法：直接用token获取用户
                try:
                    user_response = temp_client.auth.get_user(access_token)
                    logger.debug(f"获取用户信息: {user_response}")
                except Exception as user_error:
                    logger.error(f"获取用户失败: {str(user_error)}")
                    raise session_error
            
            # 更新用户密码
            response = temp_client.auth.update_user({"password": new_password})
            
            logger.debug(f"更新密码响应: {response}")
            
            if response and response.user:
                logger.info(f"密码更新成功: 用户ID={response.user.id}")
                return True
            else:
                logger.error("密码更新失败: 响应中无用户信息")
                return False
                
        except Exception as e:
            logger.error(f"使用令牌更新密码失败: {str(e)}")
            logger.exception("详细错误信息:")
            return False
    
    async def change_password(self, user_id: str, current_password: str, new_password: str) -> bool:
        """修改用户密码
        
        Args:
            user_id: 用户ID
            current_password: 当前密码
            new_password: 新密码
            
        Returns:
            是否成功修改密码
        """
        try:
            # 首先验证当前密码是否正确
            # 获取用户邮箱
            user_data = self.client.auth.admin.get_user_by_id(user_id)
            if not user_data or not user_data.user:
                logger.error(f"获取用户信息失败，用户ID: {user_id}")
                return False
            
            email = user_data.user.email
            
            # 尝试使用当前密码登录
            try:
                self.client.auth.sign_in_with_password({
                    "email": email,
                    "password": current_password
                })
            except Exception as e:
                logger.error(f"当前密码验证失败: {str(e)}")
                return False
            
            # 使用管理员API更新密码
            try:
                # 需要使用service_role密钥
                admin_client = self.client
                
                # 更新用户密码
                admin_client.auth.admin.update_user_by_id(
                    user_id,
                    {"password": new_password}
                )
                
                logger.info(f"已成功修改用户密码，用户ID: {user_id}")
                return True
            except Exception as e:
                logger.error(f"修改密码失败: {str(e)}")
                return False
                
        except Exception as e:
            logger.error(f"修改密码过程中发生错误: {str(e)}")
            return False
    
    async def get_user(self, access_token: str = None) -> Optional[UserResponse]:
        """获取当前用户信息
        
        Args:
            access_token: 可选的访问令牌
            
        Returns:
            用户信息，如果未登录则返回None
        """
        try:
            # 如果没有提供令牌，直接返回当前用户（如果已登录）
            if not access_token:
                logger.debug("没有提供访问令牌")
                return None
            
            # 记录令牌信息（安全起见只显示前10个字符）
            token_preview = access_token[:10] + "..." if len(access_token) > 10 else access_token
            logger.debug(f"尝试验证令牌: {token_preview}")
            
            # 方法1（首选）：直接通过HTTP请求调用Supabase API
            # 这种方法最可靠，因为它绕过了SDK的限制，直接与Supabase通信
            try:
                import httpx
                # 构建直接请求到Supabase Auth API的URL和头部
                url = f"{self.client.supabase_url}/auth/v1/user"
                headers = {
                    "apikey": self.client.supabase_key,
                    "Authorization": f"Bearer {access_token}"
                }
                
                logger.debug(f"直接HTTP请求获取用户信息: URL={url}")
                logger.debug(f"请求头: apikey={self.client.supabase_key[:10]}..., Authorization=Bearer {token_preview}")
                
                async with httpx.AsyncClient() as client:
                    http_response = await client.get(url, headers=headers)
                    status_code = http_response.status_code
                    
                    # 记录完整的响应信息
                    logger.debug(f"HTTP响应状态码: {status_code}")
                    logger.debug(f"HTTP响应头: {http_response.headers}")
                    logger.debug(f"HTTP响应内容: {http_response.text[:200]}")
                    
                    # 如果状态码不是200，记录详细信息并返回None
                    if status_code != 200:
                        logger.error(f"验证失败，状态码: {status_code}, 响应: {http_response.text[:200]}")
                        # 尝试下一种方法
                        raise Exception(f"HTTP请求失败: {status_code}")
                    
                    # 解析响应数据
                    user_data = http_response.json()
                    logger.debug(f"成功获取用户数据: ID={user_data.get('id')}, Email={user_data.get('email')}")
                    
                    # 验证session_id是否存在（基于文章内容，这是关键字段）
                    if not user_data.get('id'):
                        logger.warning("用户数据中没有ID字段")
                        raise Exception("无效的用户数据")
                    
                    # 返回用户响应对象
                    return UserResponse(
                        id=user_data.get('id'),
                        email=user_data.get('email'),
                        username=user_data.get('user_metadata', {}).get('username'),
                        created_at=user_data.get('created_at')
                    )
            except Exception as e1:
                logger.warning(f"直接HTTP请求方法失败: {str(e1)}")
                
                # 如果直接HTTP失败，尝试方法2
                try:
                    logger.debug("尝试使用SDK的getUser方法...")
                    # 方法2：使用Supabase SDK的getUser方法
                    response = self.client.auth.get_user(jwt=access_token)
                    
                    if not response or not response.user:
                        logger.warning("SDK getUser方法返回了空结果")
                        raise Exception("无法获取用户信息")
                    
                    logger.debug(f"SDK getUser方法成功: {response.user.email}")
                    return UserResponse(
                        id=response.user.id,
                        email=response.user.email,
                        username=response.user.user_metadata.get("username") if hasattr(response.user, 'user_metadata') else None,
                        created_at=response.user.created_at
                    )
                except Exception as e2:
                    logger.warning(f"SDK getUser方法失败: {str(e2)}")
                    
                    # 尝试方法3
                    try:
                        logger.debug("尝试使用service role key创建新客户端并获取会话...")
                        # 方法3：创建新的客户端实例并使用getSession
                        from supabase import create_client
                        
                        # 使用service role key创建客户端，这对于管理用户是必需的
                        temp_client = create_client(
                            self.client.supabase_url,
                            SUPABASE_SERVICE_ROLE_KEY,  # 使用service role key而不是anon key
                            options={"auto_refresh_token": False, "persist_session": False}
                        )
                        
                        # 使用getSession代替set_session
                        try:
                            session_response = await temp_client.auth.get_user(jwt=access_token)
                            if not session_response or not session_response.user:
                                logger.warning("getSession方法返回了空结果")
                                return None
                            
                            logger.debug(f"getSession方法成功: {session_response.user.email}")
                            return UserResponse(
                                id=session_response.user.id,
                                email=session_response.user.email,
                                username=session_response.user.user_metadata.get("username"),
                                created_at=session_response.user.created_at
                            )
                        except Exception as e:
                            logger.warning(f"getSession失败: {str(e)}")
                            # 尝试直接HTTP API调用
                            import httpx
                            url = f"{self.client.supabase_url}/auth/v1/user"
                            headers = {
                                "apikey": SUPABASE_SERVICE_ROLE_KEY,
                                "Authorization": f"Bearer {access_token}"
                            }
                            
                            async with httpx.AsyncClient() as client:
                                http_response = await client.get(url, headers=headers)
                                if http_response.status_code == 200:
                                    user_data = http_response.json()
                                    return UserResponse(
                                        id=user_data.get('id'),
                                        email=user_data.get('email'),
                                        username=user_data.get('user_metadata', {}).get('username'),
                                        created_at=user_data.get('created_at')
                                    )
                                logger.warning(f"直接HTTP请求失败: {http_response.status_code}")
                                return None
                    except Exception as e3:
                        logger.error(f"所有验证方法都失败: {str(e3)}")
                        return None
            
        except Exception as e:
            logger.error(f"获取用户信息出错: {str(e)}")
            return None
    
    def set_auth_cookie(self, response: Response, token: str, expires_in: int) -> None:
        """设置认证Cookie
        
        Args:
            response: FastAPI响应对象
            token: 访问令牌
            expires_in: 过期时间（秒）
        """
        # 确保过期时间至少为24小时
        max_age = max(expires_in, 86400)  # 86400秒 = 24小时
        
        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            max_age=max_age,
            samesite="lax",
            secure=False  # 开发环境中关闭，生产环境应设为True
        )
    
    def clear_auth_cookie(self, response: Response) -> None:
        """清除认证Cookie
        
        Args:
            response: FastAPI响应对象
        """
        # 清除标准的访问令牌Cookie
        response.delete_cookie(key="access_token")
        
        # 清除所有可能的Supabase相关Cookie
        response.delete_cookie(key="sb-access-token")
        response.delete_cookie(key="sb-refresh-token")
        response.delete_cookie(key="supabase-auth-token")
        response.delete_cookie(key="__session")
        response.delete_cookie(key="supabase.auth.token")
        
        # 清除所有当前域下的cookie（根路径和所有可能的子路径）
        for path in ["/", "/auth", "/api"]:
            response.delete_cookie(key="access_token", path=path)
            response.delete_cookie(key="sb-access-token", path=path)
            response.delete_cookie(key="sb-refresh-token", path=path)
            response.delete_cookie(key="supabase-auth-token", path=path)
            response.delete_cookie(key="__session", path=path)
            response.delete_cookie(key="supabase.auth.token", path=path)
            
        logger.debug("清除了所有可能的认证Cookie")
    
    async def verify_token(self, request: Request) -> Optional[UserResponse]:
        """验证请求中的令牌
        
        Args:
            request: FastAPI请求对象
            
        Returns:
            用户信息，如果验证失败则返回None
        """
        logger.debug(f"验证请求中的令牌: {request.headers.keys()}")
        
        # 1. 首先从Authorization头获取令牌（标准方法）
        auth_header = request.headers.get("Authorization") or request.headers.get("authorization")
        api_key = request.headers.get("apikey")
        token = None
        
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
            logger.debug(f"从Authorization头部提取令牌: {token[:10]}...")
            
            # 尝试验证
            user = await self.get_user(token)
            if user:
                logger.debug(f"使用Authorization头部令牌验证成功: {user.email}")
                return user
            else:
                logger.warning("使用Authorization头部令牌验证失败")
        
        # 2. 不要尝试使用apikey作为JWT令牌 - 这是常见错误
        # 根据Supabase文档，apikey不包含必要的'sub'声明，无法作为JWT使用
        if api_key:
            logger.debug("检测到API密钥，但不会将其用作JWT令牌")
                
        # 3. 正确使用: 同时使用Authorization头中的JWT和apikey（Supabase推荐方式）
        if token and api_key:
            # 使用两者组合直接HTTP请求验证
            try:
                import httpx
                url = f"{self.client.supabase_url}/auth/v1/user"
                headers = {
                    "apikey": api_key,
                    "Authorization": f"Bearer {token}"
                }
                
                logger.debug(f"尝试同时使用apikey和JWT令牌验证: URL={url}")
                logger.debug(f"请求头: apikey={api_key[:10]}..., Authorization=Bearer {token[:10]}...")
                
                async with httpx.AsyncClient() as client:
                    http_response = await client.get(url, headers=headers)
                    
                    if http_response.status_code == 200:
                        user_data = http_response.json()
                        logger.debug(f"同时使用apikey和JWT令牌验证成功: {user_data.get('email')}")
                        return UserResponse(
                            id=user_data.get('id'),
                            email=user_data.get('email'),
                            username=user_data.get('user_metadata', {}).get('username'),
                            created_at=user_data.get('created_at')
                        )
                    else:
                        logger.warning(f"同时使用apikey和JWT令牌验证失败: {http_response.status_code}, 响应: {http_response.text[:100]}")
            except Exception as e:
                logger.warning(f"同时使用apikey和JWT令牌验证出错: {str(e)}")
        elif token:
            # 如果只有JWT令牌，尝试使用SDK验证
            try:
                logger.debug("仅使用JWT令牌尝试SDK验证...")
                response = self.client.auth.get_user(jwt=token)
                if response and response.user:
                    logger.debug(f"仅使用JWT令牌SDK验证成功: {response.user.email}")
                    return UserResponse(
                        id=response.user.id,
                        email=response.user.email,
                        username=response.user.user_metadata.get("username"),
                        created_at=response.user.created_at
                    )
                else:
                    logger.warning("仅使用JWT令牌SDK验证失败")
            except Exception as e:
                logger.warning(f"仅使用JWT令牌SDK验证出错: {str(e)}")
        
        # 4. 最后尝试从Cookie获取令牌
        cookie_token = request.cookies.get("access_token")
        if cookie_token:
            logger.debug(f"从Cookie提取令牌: {cookie_token[:10]}...")
            user = await self.get_user(cookie_token)
            if user:
                logger.debug(f"使用Cookie令牌验证成功: {user.email}")
                return user
            else:
                logger.warning("使用Cookie令牌验证失败")
        
        # 验证失败，详细记录原因
        logger.warning("所有验证方法均失败")
        reason = []
        if not auth_header:
            reason.append("无Authorization头部")
        if not token:
            reason.append("无JWT令牌")
        if not api_key:
            reason.append("无API密钥")
        if not cookie_token:
            reason.append("无Cookie令牌")
            
        logger.warning(f"验证失败原因: {', '.join(reason)}")
        return None
    
    async def require_user(self, request: Request) -> UserResponse:
        """要求请求必须包含有效的用户令牌
        
        Args:
            request: FastAPI请求对象
            
        Returns:
            用户信息
            
        Raises:
            HTTPException: 验证失败时抛出
        """
        user = await self.verify_token(request)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="认证失败",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user
    
    async def test_auth(self, access_token: str, api_key: str = None) -> bool:
        """测试验证功能
        
        Args:
            access_token: 访问令牌
            api_key: 可选的API密钥，默认使用client.supabase_key
            
        Returns:
            验证是否成功
        """
        import httpx
        import json
        
        # 使用提供的API密钥或默认的supabase密钥
        api_key = api_key or self.client.supabase_key
        
        # 打印关键信息
        logger.info("============ 测试验证功能 ============")
        logger.info(f"Supabase URL: {self.client.supabase_url}")
        logger.info(f"令牌 (前10字符): {access_token[:10]}...")
        logger.info(f"API密钥 (前10字符): {api_key[:10]}...")
        
        # 方法1: 使用直接HTTP请求
        try:
            url = f"{self.client.supabase_url}/auth/v1/user"
            headers = {
                "apikey": api_key,
                "Authorization": f"Bearer {access_token}"
            }
            
            logger.info(f"尝试方法1 - 直接HTTP请求: URL={url}")
            logger.debug(f"完整请求头: {json.dumps(headers)}")
            
            async with httpx.AsyncClient() as client:
                http_response = await client.get(url, headers=headers)
                status_code = http_response.status_code
                
                logger.info(f"HTTP响应状态码: {status_code}")
                logger.debug(f"HTTP响应头: {http_response.headers}")
                logger.debug(f"HTTP响应内容: {http_response.text[:500]}")
                
                if status_code == 200:
                    logger.info("方法1验证成功!")
                    return True
                else:
                    logger.warning(f"方法1验证失败: {status_code}")
        except Exception as e:
            logger.error(f"方法1出错: {str(e)}")
        
        # 方法2: 使用SDK
        try:
            logger.info("尝试方法2 - 使用SDK的getUser方法")
            response = self.client.auth.get_user(jwt=access_token)
            
            if response and response.user:
                logger.info(f"方法2验证成功! 用户: {response.user.email}")
                return True
            else:
                logger.warning("方法2验证失败: 未获取到用户")
        except Exception as e:
            logger.error(f"方法2出错: {str(e)}")
        
        # 方法3: 检查令牌格式
        try:
            logger.info("尝试方法3 - 解码JWT令牌")
            
            # 不验证签名，只解码
            decoded = jwt.decode(access_token, options={"verify_signature": False})
            logger.info(f"JWT解码成功: {json.dumps(decoded)}")
            
            # 检查关键字段
            if "sub" in decoded:
                logger.info(f"令牌包含'sub'字段: {decoded['sub']}")
            else:
                logger.warning("令牌不包含'sub'字段 - 这可能是错误的根源!")
                
            return False
        except jwt.InvalidTokenError as e:
            logger.error(f"JWT解码错误: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"方法3出错: {str(e)}")
            
        logger.info("所有验证方法均失败")
        return False 