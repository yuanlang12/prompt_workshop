from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from datetime import datetime, timedelta
from database import Database
from auth import create_access_token, get_current_user, UserInfo, Token
import uuid
import os

router = APIRouter()

# 数据库实例
db = Database(os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts.db"))

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """临时登录端点 - 后续将替换为Authing OAuth流程"""
    # 默认使用本地用户账号，用于测试
    with db.get_connection() as conn:
        user = conn.execute("SELECT * FROM users WHERE username = ?", ("本地用户",)).fetchone()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 创建访问令牌
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user["id"]}, expires_delta=access_token_expires
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=1800  # 30分钟 = 1800秒
    )

@router.get("/login-temp")
async def temp_login_page():
    """临时登录页面 - 后续将替换为Authing OAuth流程"""
    # 获取默认用户
    with db.get_connection() as conn:
        user = conn.execute("SELECT * FROM users WHERE username = ?", ("本地用户",)).fetchone()
    
    if not user:
        # 创建默认用户
        user_id = str(uuid.uuid4())
        created_at = datetime.now().isoformat()
        
        with db.get_connection() as conn:
            conn.execute("""
            INSERT INTO users (id, authing_id, username, email, created_at)
            VALUES (?, ?, ?, ?, ?)
            """, (user_id, "local_user", "本地用户", "", created_at))
            conn.commit()
        
        # 获取新创建的用户
        with db.get_connection() as conn:
            user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    
    # 创建访问令牌
    access_token_expires = timedelta(minutes=60)
    access_token = create_access_token(
        data={"sub": user["id"]}, expires_delta=access_token_expires
    )
    
    # 创建带有Cookie的响应
    response = RedirectResponse(url="/")
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=3600,  # 1小时 = 3600秒
        secure=False,  # 开发环境下设为False
        samesite="lax"
    )
    
    return response

@router.get("/me", response_model=UserInfo)
async def read_users_me(request: Request, current_user: UserInfo = Depends(get_current_user)):
    """获取当前用户信息"""
    return current_user 