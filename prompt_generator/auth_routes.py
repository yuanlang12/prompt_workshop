"""
认证相关路由
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Form
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
import os
import logging
from typing import Optional
import time

from supabase_auth import SupabaseAuthService
from supabase_models import UserCreate, UserLogin, TokenResponse
from supabase_db import SupabaseDB
from auth_utils import success_response

# 配置日志
logger = logging.getLogger(__name__)

# 创建路由
router = APIRouter(prefix="/auth", tags=["认证"])

# 模板目录
templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
templates = Jinja2Templates(directory=templates_dir)

# 创建认证服务实例
auth_service = SupabaseAuthService()

@router.post("/register", response_class=HTMLResponse)
async def register(request: Request, email: str = Form(...), password: str = Form(...), username: str = Form(None)):
    """注册新用户并根据结果跳转到相应页面"""
    # 检查请求可能是要求JSON响应
    accept_header = request.headers.get("accept", "")
    wants_json = "application/json" in accept_header
    
    try:
        user_data = UserCreate(email=email, password=password, username=username)
        result = await auth_service.register_user(user_data)
        
        # 检查注册结果
        if result and result.get("success"):
            logger.info(f"用户 {email} 注册成功，需要邮箱验证")
            # 直接返回重定向响应
            return RedirectResponse(
                url=f"/auth/verify-email-page?email={email}",
                status_code=303
            )
        else:
            # 如果注册失败但没有抛出异常
            logger.error("注册失败：无效的响应")
            if wants_json:
                return JSONResponse(
                    content={"success": False, "message": "注册失败，请稍后重试"},
                    status_code=400
                )
            else:
                return templates.TemplateResponse(
                    "register.html",
                    {
                        "request": request,
                        "error": "注册失败，请稍后重试",
                        "email": email
                    },
                    status_code=400
                )
        
    except Exception as e:
        error_message = str(e)
        logger.error(f"注册失败: {error_message}")
        logger.error(f"异常类型: {type(e).__name__}")
        
        # 默认错误代码
        error_code = "registration_failed"
        status_code = 400
        
        # 判断错误类型
        if "Password should contain" in error_message:
            error_message = "密码必须同时包含大写字母、小写字母和数字"
            error_code = "invalid_password"
            status_code = 422
        elif "User already registered" in error_message or "user_already_exists" in error_message.lower():
            error_message = "该邮箱已被注册，请直接登录或使用其他邮箱"
            error_code = "user_already_exists"
            status_code = 422
        
        # 尝试从错误对象中提取Supabase的错误代码
        try:
            if hasattr(e, 'response') and hasattr(e.response, 'text'):
                import json
                response_data = json.loads(e.response.text)
                if 'code' in response_data:
                    supabase_error = response_data.get('code')
                if 'error_code' in response_data:
                    supabase_error = response_data.get('error_code')
                if 'error' in response_data:
                    error_message = response_data.get('error', error_message)
                if 'msg' in response_data:
                    error_message = response_data.get('msg', error_message)
                
                # 如果是已注册用户的错误
                if supabase_error == "user_already_exists" or supabase_error == 23505:
                    error_code = "user_already_exists"
                    error_message = "该邮箱已被注册，请直接登录或使用其他邮箱"
        except Exception as parse_error:
            logger.error(f"解析错误响应失败: {str(parse_error)}")
        
        # 返回错误响应
        if wants_json:
            return JSONResponse(
                content={
                    "success": False, 
                    "detail": error_message,
                    "error_code": error_code,
                    "email": email
                },
                status_code=status_code
            )
        else:
            # 返回到注册页面并显示错误信息
            return templates.TemplateResponse(
                "register.html", 
                {
                    "request": request, 
                    "error": error_message,
                    "show_login_link": error_code == "user_already_exists",
                    "email": email
                },
                status_code=status_code
            )

# 检查邮箱是否已注册
@router.post("/check-email")
async def check_email(request: Request):
    """检查邮箱是否已注册，用于统一认证流程"""
    try:
        data = await request.json()
        email = data.get("email", "").strip().lower()
        
        if not email:
            raise HTTPException(status_code=400, detail="请输入邮箱地址")
        
        # 调用 Supabase 检查用户是否存在
        exists = await auth_service.check_user_exists(email)
        
        return {"exists": exists}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"检查邮箱出错: {e}")
        raise HTTPException(status_code=500, detail="服务器错误")

# 统一认证页面
@router.get("", response_class=HTMLResponse)
async def auth_page(request: Request):
    """统一的认证页面 - 动态切换登录/注册"""
    # 如果用户已登录，重定向到首页
    user = await auth_service.verify_token(request)
    if user:
        return RedirectResponse(url="/", status_code=302)
    
    return templates.TemplateResponse("auth.html", {"request": request})

@router.post("/login", response_model=TokenResponse)
async def login(login_data: UserLogin, response: Response):
    """用户登录
    
    Args:
        login_data: 用户登录信息
        
    Returns:
        令牌和用户信息
    """
    try:
        # 登录用户
        token_response = await auth_service.login_user(login_data)
        
        # 设置Cookie
        auth_service.set_auth_cookie(
            response=response,
            token=token_response.access_token,
            expires_in=token_response.expires_in
        )
        
        return token_response
    except Exception as e:
        error_message = str(e)
        logger.error(f"登录失败: {error_message}")
        
        # 根据错误类型返回友好的错误信息
        if "Invalid login credentials" in error_message:
            error_message = "邮箱或密码错误，请重试"
        elif "User not found" in error_message:
            error_message = "该邮箱未注册，请先注册"
        elif "Email not confirmed" in error_message or "not confirmed" in error_message.lower():
            error_message = "邮箱未验证，请先查收邮件并点击验证链接。如未收到验证邮件，请检查垃圾邮件或联系管理员重新发送。"
        else:
            error_message = "登录失败，请稍后重试"
            
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_message
        )

@router.post("/logout")
async def logout(response: Response, request: Request):
    """用户登出，清除所有会话数据
    
    Returns:
        直接返回登录页面HTML，而不是重定向
    """
    try:
        # 登出用户（此过程不要依赖于是否成功）
        try:
            await auth_service.logout_user()
        except Exception as e:
            logger.error(f"Supabase登出错误（将忽略）: {str(e)}")
        
        # 清除所有可能的cookie
        # 标准cookie
        response.delete_cookie("access_token")
        # Supabase相关cookie
        response.delete_cookie("sb-access-token")
        response.delete_cookie("sb-refresh-token") 
        response.delete_cookie("supabase-auth-token")
        response.delete_cookie("sb-provider-token")
        response.delete_cookie("sb-refresh-token")
        response.delete_cookie("sb-access-token")
        response.delete_cookie("sb-auth-token")
        response.delete_cookie("__session")
        response.delete_cookie("supabase.auth.token")
        
        # 确保在所有可能的路径下清除
        for path in ["/", "/auth", "/api", "/auth/logout"]:
            response.delete_cookie("access_token", path=path)
            response.delete_cookie("sb-access-token", path=path)
            response.delete_cookie("sb-refresh-token", path=path)
            response.delete_cookie("supabase-auth-token", path=path)
            response.delete_cookie("sb-provider-token", path=path)
            response.delete_cookie("sb-refresh-token", path=path)
            response.delete_cookie("sb-access-token", path=path)
            response.delete_cookie("sb-auth-token", path=path)
            response.delete_cookie("__session", path=path)
            response.delete_cookie("supabase.auth.token", path=path)
        
        # 记录日志
        logger.info("用户退出登录，所有Cookie已清除")
        
        # 重要！不使用重定向，直接返回HTML，强制浏览器完全加载新页面
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>退出登录中...</title>
            <script>
            // 清除所有存储
            function clearAll() {
                try {
                    // 清除localStorage
                    localStorage.clear();
                    // 清除sessionStorage
                    sessionStorage.clear();
                    // 清除所有cookie
                    document.cookie.split(";").forEach(function(c) {
                        document.cookie = c.trim().split("=")[0] + "=;expires=Thu, 01 Jan 1970 00:00:00 UTC;path=/;";
                    });
                    console.log("已清除所有本地存储");
                    
                    // 设置登出标记
                    sessionStorage.setItem('just_logged_out', 'true');
                    
                    // 跳转到登录页面
                    window.location.replace("/auth/login-page?logout=success");
                } catch (error) {
                    console.error("清除存储时出错:", error);
                    window.location.replace("/auth/login-page?logout=error");
                }
            }
            // 页面加载完立即执行
            window.onload = clearAll;
            </script>
        </head>
        <body>
            <p>正在退出登录，请稍候...</p>
        </body>
        </html>
        """
        
        return HTMLResponse(content=html_content)
    except Exception as e:
        logger.error(f"退出登录过程中出错: {str(e)}")
        # 返回错误信息但仍然尝试清除cookie
        response.delete_cookie("access_token")
        return HTMLResponse(content=f"退出登录出错: {str(e)}, 请关闭浏览器或<a href='/auth/login-page'>点击这里</a>返回登录页面")

@router.post("/reset-password")
async def reset_password(email: str = Form(...)):
    """发送密码重置邮件
    
    Args:
        email: 用户邮箱
        
    Returns:
        成功消息
    """
    # 发送密码重置邮件
    result = await auth_service.reset_password(email)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="密码重置邮件发送失败"
        )
    
    return {"message": "密码重置邮件已发送"}

@router.post("/update-password")
async def update_password(access_token: str = Form(...), new_password: str = Form(...)):
    """使用重置令牌更新密码
    
    Args:
        access_token: 密码重置令牌
        new_password: 新密码
        
    Returns:
        成功消息
    """
    try:
        # 使用access_token更新用户密码
        result = await auth_service.update_password_with_token(access_token, new_password)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="密码更新失败"
            )
        
        return {"message": "密码更新成功"}
    except Exception as e:
        error_msg = str(e)
        logger.error(f"更新密码失败: {error_msg}")
        
        # 提供更友好的错误消息
        if "Password should contain" in error_msg or "weak password" in error_msg.lower():
            detail = "密码强度不够：密码必须包含大写字母、小写字母和数字"
        elif "Invalid" in error_msg or "invalid" in error_msg:
            detail = "密码重置链接无效或已过期，请重新申请密码重置"
        else:
            detail = f"密码更新失败: {error_msg}"
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )

@router.get("/me")
async def get_current_user(request: Request):
    """获取当前用户信息
    
    Returns:
        用户信息
    """
    # 增加详细的调试日志
    logger.debug(f"请求头信息: {dict(request.headers)}")
    
    # 检查授权相关的请求头
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    api_key = request.headers.get("apikey") or request.headers.get("Apikey")
    
    # 详细记录授权信息
    if auth_header:
        logger.debug(f"Authorization头部存在: {auth_header[:15]}...")
        if not auth_header.startswith("Bearer "):
            logger.warning("Authorization头部格式错误，应为'Bearer <token>'")
    else:
        logger.warning("Authorization头部不存在 - Supabase验证需要JWT")
        
    if api_key:
        logger.debug(f"API密钥存在: {api_key[:15]}...")
    else:
        logger.warning("API密钥不存在 - Supabase验证可能需要apikey")
    
    # 获取并验证当前用户
    try:
        logger.debug("开始验证用户...")
        user = await auth_service.verify_token(request)
        
        if not user:
            logger.error("用户验证失败: 未返回用户信息")
            logger.debug("尝试 401 状态码响应")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="认证失败: JWT令牌可能无效或已过期"
            )
        
        logger.info(f"用户验证成功: {user.email}")
        return user
    except Exception as e:
        logger.error(f"用户验证过程中发生错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"认证失败: {str(e)}"
        )

@router.get("/login-page")
async def login_page(request: Request):
    """登录页面
    
    Returns:
        登录页面HTML
    """
    # 检查用户是否已登录
    user = await auth_service.verify_token(request)
    
    # 获取URL查询参数
    message = request.query_params.get("message", "")
    error = request.query_params.get("error", "")
    email = request.query_params.get("email", "")
    logout = request.query_params.get("logout", "")
    
    # 如果已登录并且不是从退出登录页面过来的，重定向到首页
    if user and not logout:
        return RedirectResponse(url="/")
    
    # 构建模板上下文
    context = {
        "request": request,
        "message": message,
        "error": error,
        "email": email,
        "logout_success": logout == "success",
        "clear_storage": True,  # 总是触发前端清除本地存储的标志
        "timestamp": int(time.time())  # 添加时间戳防止缓存
    }
    
    # 如果是从退出登录页面过来的，添加相应的消息
    if logout == "success":
        context["message"] = "您已成功退出登录"
    elif logout == "error":
        context["error"] = "退出登录过程中出现一些问题，但您已被强制登出"
    
    # 返回模板响应，并设置响应头防止缓存
    response = templates.TemplateResponse("login.html", context)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    
    return response

@router.get("/register-page")
async def register_page(request: Request):
    """注册页面
    
    Returns:
        注册页面HTML
    """
    # 直接渲染注册页面，不检查登录状态
    return templates.TemplateResponse("register.html", {"request": request})

@router.get("/reset-password-page")
async def reset_password_page(request: Request):
    """密码重置页面
    
    Returns:
        密码重置页面HTML
    """
    # 渲染密码重置页面，用于处理Supabase密码重置链接
    return templates.TemplateResponse("reset_password.html", {"request": request})

# 临时登录功能（开发测试用）
@router.get("/login-temp")
async def temp_login(response: Response):
    """临时登录（仅供开发测试）
    
    Returns:
        重定向到首页
    """
    try:
        # 使用测试账号登录
        login_data = UserLogin(
            email="test@example.com",
            password="password123"
        )
        
        token_response = await auth_service.login_user(login_data)
        
        # 设置Cookie
        auth_service.set_auth_cookie(
            response=response,
            token=token_response.access_token,
            expires_in=token_response.expires_in
        )
        
        # 重定向到首页
        return RedirectResponse(url="/")
    except Exception as e:
        logger.error(f"临时登录失败: {str(e)}")
        # 重定向到登录页面
        return RedirectResponse(url="/auth/login-page")

@router.get("/test-auth")
async def test_auth(request: Request, token: str, apikey: str = None):
    """测试认证功能
    
    Args:
        token: 要测试的令牌
        apikey: 可选的API密钥
    
    Returns:
        测试结果
    """
    # 记录测试信息
    logger.info(f"测试认证 - Token: {token[:10]}...")
    if apikey:
        logger.info(f"测试认证 - APIKey: {apikey[:10]}...")
    
    # 使用测试方法验证令牌
    result = await auth_service.test_auth(token, apikey)
    
    return {
        "success": result,
        "message": "认证测试成功" if result else "认证测试失败"
    }

@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    """用户个人资料页面"""
    try:
        # 验证用户
        user = await auth_service.verify_token(request)
        if not user:
            return RedirectResponse(url="/auth/login-page?message=请先登录", status_code=303)
        
        # 获取用户的项目
        db = SupabaseDB()
        projects = await db.get_user_projects(user.id)
        
        # 获取查询参数
        message = request.query_params.get("message")
        error = request.query_params.get("error")
        
        return templates.TemplateResponse(
            "profile.html", 
            {
                "request": request, 
                "user": user, 
                "projects": projects,
                "message": message,
                "error": error
            }
        )
    except Exception as e:
        logger.error(f"加载个人资料页面失败: {str(e)}")
        return RedirectResponse(url="/auth/login-page?message=会话已过期，请重新登录", status_code=303)

@router.post("/change-password", response_class=HTMLResponse)
async def change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...)
):
    """修改用户密码"""
    try:
        # 验证用户
        user = await auth_service.verify_token(request)
        if not user:
            return RedirectResponse(url="/auth/login-page?message=请先登录", status_code=303)
        
        # 验证新密码和确认密码是否匹配
        if new_password != confirm_password:
            return RedirectResponse(url="/auth/profile?error=新密码和确认密码不匹配", status_code=303)
        
        # 调用认证服务修改密码
        result = await auth_service.change_password(user.id, current_password, new_password)
        
        if result:
            return RedirectResponse(url="/auth/profile?message=密码修改成功", status_code=303)
        else:
            return RedirectResponse(url="/auth/profile?error=密码修改失败，请检查当前密码是否正确", status_code=303)
    except Exception as e:
        logger.error(f"修改密码失败: {str(e)}")
        return RedirectResponse(url="/auth/profile?error=修改密码时发生错误: {str(e)}", status_code=303)

@router.post("/resend-verification")
async def resend_verification(request: Request, email: str):
    """重新发送验证邮件"""
    try:
        # 调用Supabase的重新发送验证邮件API
        await auth_service.resend_verification_email(email)
        return JSONResponse(
            content={"success": True, "message": "验证邮件已重新发送"},
            status_code=200
        )
    except Exception as e:
        error_message = str(e)
        logger.error(f"重新发送验证邮件失败: {error_message}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="重新发送验证邮件失败，请稍后再试"
        )

@router.get("/verify-email-page")
async def verify_email_page(request: Request, email: str):
    """验证邮箱页面
    
    Returns:
        验证邮箱页面HTML
    """
    return templates.TemplateResponse(
        "verify_email.html",
        {"request": request, "email": email}
    ) 