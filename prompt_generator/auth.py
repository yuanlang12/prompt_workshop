from fastapi import Depends, HTTPException, status, Request, Cookie
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pydantic import BaseModel
import os
import secrets
import uuid
from database import Database
import logging
from supabase_auth import SupabaseAuthService
from supabase_client import supabase

# 配置日志
logger = logging.getLogger(__name__)

# JWT签名密钥 - 仅用于旧版本地令牌的兼容
# 生产环境请通过环境变量 SECRET_KEY 设置（可用 openssl rand -hex 32 生成）
# 未设置时每次启动随机生成，重启后旧令牌失效
SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_hex(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 设置令牌过期时间为24小时

# 令牌模型
class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int

# 用户模型
class UserInfo(BaseModel):
    id: str
    username: str
    email: Optional[str] = None

# 使用 HTTPBearer 而不是 OAuth2PasswordBearer，这样可以更灵活地处理令牌
security = HTTPBearer(auto_error=False)

# 数据库实例
db = Database(os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts.db"))

# 创建Supabase认证服务实例
supabase_auth = SupabaseAuthService()

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """创建访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# 从令牌中提取和验证用户
def get_user_from_token(token: str) -> Optional[UserInfo]:
    """从令牌中提取和验证用户信息（兼容原有认证系统）"""
    try:
        # 解码令牌
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # 获取用户ID
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        # 从数据库获取用户信息
        user = db.get_user(user_id)
        if not user:
            return None
        
        # 返回用户信息
        return UserInfo(
            id=user["id"],
            username=user["username"],
            email=user.get("email")
        )
    except jwt.InvalidTokenError:
        # 如果JWT解码失败，可能是Supabase的令牌，尝试用Supabase验证
        logger.info("原系统JWT解码失败，尝试使用Supabase验证")
        return None
    except Exception as e:
        logger.error(f"令牌验证过程中出错: {str(e)}")
        return None

# 添加仅用于调试的函数
def debug_token(token: str) -> Dict:
    """解码令牌并返回内容（仅用于调试）"""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_signature": False})
    except:
        return {"error": "无效的令牌格式"}

async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    access_token: Optional[str] = Cookie(None)
) -> UserInfo:
    """获取当前用户
    
    优先尝试Supabase认证，然后尝试原系统认证
    """
    token = None
    
    # 先尝试从Authorization头中获取令牌
    if credentials and credentials.credentials:
        logger.debug(f"从Authorization头获取令牌")
        token = credentials.credentials
    
    # 如果没有Authorization头，尝试从Cookie中获取
    if not token and access_token:
        logger.debug(f"从Cookie获取令牌")
        token = access_token
    
    if not token:
        logger.warning("未找到认证令牌")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的身份验证凭据",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 优先使用Supabase验证
    try:
        logger.debug(f"尝试Supabase令牌验证")
        user = await supabase_auth.get_user(token)
        if user:
            logger.info(f"Supabase验证成功: 用户ID={user.id}")
            # 转换为应用的UserInfo模型
            return UserInfo(
                id=user.id,
                username=user.username or user.email.split("@")[0],
                email=user.email
            )
    except Exception as e:
        logger.error(f"Supabase验证出错: {str(e)}")
    
    # 如果Supabase验证失败，尝试原系统验证
    logger.debug(f"尝试原系统令牌验证")
    user = get_user_from_token(token)
    if user:
        logger.info(f"原系统验证成功: 用户ID={user.id}")
        return user
    
    # 如果所有验证方式都失败，抛出401错误
    logger.warning("所有认证方式均失败")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的身份验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )

async def get_user_from_cookie(request):
    """从Cookie中获取用户信息 (用于非API路由)"""
    token = request.cookies.get("access_token")
    if not token:
        return None
    
    # 优先使用Supabase验证
    try:
        user = await supabase_auth.get_user(token)
        if user:
            # 转换为应用的UserInfo模型
            return UserInfo(
                id=user.id,
                username=user.username or user.email.split("@")[0],
                email=user.email
            )
    except Exception:
        pass
    
    # 如果Supabase验证失败，尝试原系统验证
    return get_user_from_token(token)

# 为Authing认证预留的函数，后续实现
async def verify_authing_token(token: str) -> Dict[str, Any]:
    """验证Authing令牌 (预留，后续实现)"""
    # 这只是一个占位符，后续会实现实际的Authing令牌验证
    return {"sub": "authing_user_id", "name": "Authing用户"} 