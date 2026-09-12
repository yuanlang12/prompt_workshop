"""
项目操作工具函数
提供项目重命名和删除的增强功能
"""

import logging
from typing import Optional, Dict, Any, List

from supabase_client import get_supabase_admin_client

logger = logging.getLogger(__name__)

async def rename_project(project_id: str, new_name: str, supabase_db, user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    增强的项目重命名功能

    Args:
        project_id: 项目ID
        new_name: 新的项目名称
        supabase_db: Supabase数据库实例
        user_id: 当前用户ID，提供时在数据库层附加归属过滤

    Returns:
        更新后的项目信息
    """
    logger.info(f"重命名项目 {project_id} 为 {new_name}")

    # 使用现有的方法重命名项目
    return await supabase_db.update_project(project_id, name=new_name, user_id=user_id)

async def delete_project_with_history(project_id: str, supabase_db, user_id: Optional[str] = None) -> bool:
    """
    增强的项目删除功能，确保删除项目的所有相关数据
    包括：
    - 项目关联的提示词历史记录
    - 项目中的所有提示词
    - 项目本身

    Args:
        project_id: 项目ID
        supabase_db: Supabase数据库实例
        user_id: 当前用户ID，提供时先校验项目归属再执行删除

    Returns:
        删除是否成功
    """
    # 0. 先校验项目归属，避免级联删除他人项目的数据
    if user_id:
        project = await supabase_db.get_project(project_id, user_id=user_id)
        if not project:
            logger.warning(f"项目不存在或不属于该用户，取消删除: {project_id}")
            return False

    def _sync_delete_op():
        try:
            # 获取管理员客户端
            admin_client = get_supabase_admin_client()
            if not admin_client:
                logger.error("无法获取管理员客户端")
                return False
                    
            # 1. 先删除项目关联的所有提示词历史记录
            logger.info(f"删除项目 {project_id} 的所有提示词历史记录")
            try:
                history_response = admin_client.table("prompt_history").delete().eq("project_id", project_id).execute()
                logger.info(f"历史记录删除结果: {history_response.data}")
            except Exception as e:
                logger.error(f"删除历史记录时出错: {str(e)}")
                # 继续执行，不中断流程
            
            # 2. 删除项目中的所有提示词
            logger.info(f"删除项目 {project_id} 的所有提示词")
            try:
                prompts_response = admin_client.table("prompts").delete().eq("project_id", project_id).execute()
                logger.info(f"提示词删除结果: {prompts_response.data}")
            except Exception as e:
                logger.error(f"删除提示词时出错: {str(e)}")
                # 继续执行，不中断流程
            
            # 3. 最后删除项目本身
            logger.info(f"删除项目 {project_id}")
            try:
                project_response = admin_client.table("projects").delete().eq("id", project_id).execute()
                if project_response.data:
                    logger.info(f"项目删除成功: {project_id}")
                    return True
                else:
                    logger.error(f"项目删除失败: 响应中没有数据")
                    return False
            except Exception as e:
                logger.error(f"删除项目时出错: {str(e)}")
                return False
                
        except Exception as e:
            logger.error(f"项目删除过程出错: {str(e)}")
            return False

    import asyncio
    return await asyncio.to_thread(_sync_delete_op)