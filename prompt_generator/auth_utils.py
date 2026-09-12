"""
认证工具模块 - 用于API端点改造
提供用户认证和错误处理的通用功能
"""

import logging
import uuid
from typing import Optional, Dict, Any, Union
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from supabase_auth import SupabaseAuthService
from supabase_models import UserResponse

# 配置日志
logger = logging.getLogger(__name__)

# 创建认证服务实例
auth_service = SupabaseAuthService()

async def get_current_user(request: Request) -> Optional[UserResponse]:
    """
    从请求中提取当前登录用户
    
    Args:
        request: FastAPI请求对象
        
    Returns:
        UserResponse: 如果认证成功，返回用户信息
        None: 如果认证失败或未提供认证信息
    """
    try:
        # 使用现有的auth_service.verify_token方法验证令牌
        user = await auth_service.verify_token(request)
        return user
    except Exception as e:
        logger.error(f"认证错误: {str(e)}")
        return None

def error_response(
    status_code: int, 
    message: str, 
    error_code: str = None,
    details: Dict[str, Any] = None
) -> JSONResponse:
    """
    生成统一格式的错误响应
    
    Args:
        status_code: HTTP状态码
        message: 错误信息
        error_code: 可选的错误代码
        details: 可选的错误详情
        
    Returns:
        JSONResponse: 格式化的错误响应
    """
    response = {
        "success": False,
        "message": message
    }
    
    if error_code:
        response["error_code"] = error_code
        
    if details:
        response["details"] = details
        
    return JSONResponse(
        status_code=status_code,
        content=response
    )

def success_response(
    data: Union[Dict[str, Any], list] = None,
    message: str = "操作成功",
    status_code: int = 200,
) -> JSONResponse:
    """
    生成统一格式的成功响应
    
    Args:
        data: 响应数据
        message: 成功信息
        status_code: HTTP状态码
        
    Returns:
        JSONResponse: 格式化的成功响应
    """
    response = {
        "success": True,
        "message": message
    }
    
    if data is not None:
        response["data"] = data
        
    return JSONResponse(
        status_code=status_code,
        content=response
    )

def require_auth(user: Optional[UserResponse]) -> Optional[JSONResponse]:
    """
    验证用户是否已认证，如果未认证则返回错误响应
    
    Args:
        user: 用户对象或None
        
    Returns:
        JSONResponse: 如果未认证，返回401错误响应
        None: 如果已认证，返回None
    """
    if not user:
        return error_response(
            status_code=401,
            message="未授权访问，请先登录",
            error_code="unauthorized"
        )
    return None

def check_permission(user: UserResponse, resource_user_id: str) -> Optional[JSONResponse]:
    """
    检查用户是否有权限访问指定资源
    
    Args:
        user: 用户对象
        resource_user_id: 资源所属用户ID
        
    Returns:
        JSONResponse: 如果无权限，返回403错误响应
        None: 如果有权限，返回None
    """
    if user.id != resource_user_id:
        return error_response(
            status_code=403, 
            message="没有权限访问此资源",
            error_code="forbidden"
        )
    return None 