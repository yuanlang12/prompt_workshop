"""
Supabase数据库访问工具类
提供统一的CRUD操作接口，替代SQLite数据库
"""

import logging
import uuid
import json
from typing import List, Dict, Any, Optional, Union
from datetime import datetime

from supabase_client import supabase, init_supabase, get_supabase_admin_client
from supabase_models import (
    ProjectCreate, ProjectResponse, ProjectUpdate,
    PromptCreate, PromptResponse, PromptUpdate
)

# 配置日志
logger = logging.getLogger(__name__)

class SupabaseDB:
    """Supabase数据库访问工具类"""
    
    def __init__(self):
        """初始化Supabase客户端"""
        # 配置缺失/无效时不让应用崩溃：页面仍可访问，
        # 数据操作在实际调用时通过 client 属性给出明确错误
        self._client = supabase or init_supabase()
        if self._client is None:
            logger.warning(
                "Supabase 客户端不可用：请检查 SUPABASE_URL / SUPABASE_KEY 配置"
                "（参考 config/.env.example），登录与数据功能将不可用"
            )

        # 添加错误信息属性
        self.last_error = None

    @property
    def client(self):
        """Supabase客户端，未配置时在使用处抛出带配置指引的异常"""
        if self._client is None:
            raise Exception(
                "Supabase客户端未初始化：请检查 SUPABASE_URL / SUPABASE_KEY 配置"
                "（参考 config/.env.example 与 docs/supabase_setup.sql）"
            )
        return self._client
    
    def get_admin_client(self):
        """获取管理员权限的Supabase客户端，用于管理员操作"""
        admin_client = get_supabase_admin_client()
        if admin_client is None:
            logger.error("无法获取Supabase管理员客户端")
            raise Exception("无法获取Supabase管理员客户端")
        return admin_client
    
    # 项目相关操作 - 异步改造
    async def create_project(self, name: str, description: Optional[str] = None, user_id: str = None) -> Dict[str, Any]:
        """异步创建新项目"""
        def _sync_create():
            try:
                # 准备项目数据
                project_data = {
                    "name": name,
                    "description": description
                }
                
                # 如果提供了用户ID，则使用它，否则获取当前用户ID
                if user_id:
                    logger.debug(f"使用提供的用户ID创建项目: {user_id}")
                    project_data["user_id"] = user_id
                else:
                    logger.debug("尝试获取当前登录用户...")
                    current_user = self._get_current_user_sync()
                    if current_user:
                        logger.debug(f"当前用户ID: {current_user['id']}")
                        project_data["user_id"] = current_user["id"]
                    else:
                        logger.error("创建项目失败: 未登录或无法获取当前用户")
                        return None
                
                logger.debug(f"准备插入项目数据: {project_data}")
                
                if "user_id" not in project_data or not project_data["user_id"]:
                    logger.error("创建项目失败: 用户ID为空")
                    return None
                    
                # 使用管理员客户端插入数据
                try:
                    admin_client = self.get_admin_client()
                    if not admin_client:
                        logger.error("无法获取管理员客户端，创建项目失败")
                        self.last_error = "无法获取管理员客户端"
                        return None
                    
                    logger.debug("使用管理员客户端创建项目，绕过RLS策略")
                    response = admin_client.table("projects").insert(project_data).execute()
                    
                    if response.data and len(response.data) > 0:
                        logger.info(f"项目创建成功: {response.data[0]['id']}")
                        return response.data[0]
                    else:
                        logger.error(f"项目创建失败: 没有返回数据，响应: {response}")
                        return None
                except Exception as db_error:
                    logger.error(f"数据库插入错误: {str(db_error)}")
                    self.last_error = str(db_error)
                    error_str = str(db_error).lower()
                    if "foreign key" in error_str or "constraint" in error_str:
                        self.last_error = "外键约束错误，检查用户ID是否有效"
                    elif "permission" in error_str or "denied" in error_str:
                        self.last_error = "权限错误，检查数据库权限设置"
                    return None
            except Exception as e:
                logger.error(f"项目创建出错: {str(e)}")
                import traceback
                logger.error(f"异常堆栈: {traceback.format_exc()}")
                self.last_error = str(e)
                return None

        # 在线程池中执行同步逻辑，避免阻塞事件循环
        import asyncio
        return await asyncio.to_thread(_sync_create)
    
    async def get_projects(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """异步获取项目列表"""
        def _sync_get():
            try:
                if not user_id:
                    logger.warning("获取项目列表: 未提供用户ID")
                    return []
                    
                logger.debug(f"获取用户 {user_id} 的项目列表")
                
                try:
                    admin_client = self.get_admin_client()
                    if not admin_client:
                        logger.error("无法获取管理员客户端")
                        return []
                    
                    query = admin_client.table("projects").select("*").eq("user_id", user_id)
                    response = query.order("created_at", desc=True).execute()
                    
                    logger.debug(f"获取项目列表响应: count={len(response.data) if response.data else 0}")
                    
                    if response.data:
                        logger.info(f"找到 {len(response.data)} 个项目属于用户 {user_id}")
                        return response.data
                    else:
                        logger.warning(f"用户 {user_id} 没有任何项目")
                        return []
                except Exception as db_error:
                    logger.error(f"管理员客户端获取失败: {str(db_error)}")
                    logger.info("尝试使用普通客户端获取项目列表...")
                    query = self.client.table("projects").select("*").eq("user_id", user_id)
                    response = query.order("created_at", desc=True).execute()
                    return response.data if response.data else []
            except Exception as e:
                logger.error(f"获取项目列表出错: {str(e)}")
                return []

        import asyncio
        return await asyncio.to_thread(_sync_get)

    async def get_project(self, project_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """异步获取项目详情（提供 user_id 时附加归属过滤，防止越权读取）"""
        def _sync_get():
            try:
                logger.debug(f"尝试获取项目: {project_id}")
                admin_client = self.get_admin_client()
                if not admin_client:
                    return None

                query = admin_client.table("projects").select("*").eq("id", project_id)
                if user_id:
                    query = query.eq("user_id", user_id)
                response = query.execute()
                
                if response.data and len(response.data) > 0:
                    project = response.data[0]
                    logger.debug(f"成功获取项目: {project.get('name')}")
                    return project
                else:
                    logger.error(f"项目不存在: {project_id}")
                    return None
            except Exception as e:
                logger.error(f"获取项目详情出错: {str(e)}")
                return None

        import asyncio
        return await asyncio.to_thread(_sync_get)
    
    async def update_project(self, project_id: str, name: Optional[str] = None,
                      description: Optional[str] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
        """异步更新项目信息（提供 user_id 时附加归属过滤，防止越权修改）"""
        def _sync_update():
            try:
                update_data = {}
                if name is not None:
                    update_data["name"] = name
                if description is not None:
                    update_data["description"] = description
                
                if not update_data:
                    # 复用同步逻辑比较麻烦，这里直接重新获取一下
                    # 注意：这里不能调用 await self.get_project，因为我们在 sync wrapper 里
                    # 所以需要重新实现获取逻辑或拆分 _get_sync _create_sync 等
                    # 简单起见，直接 reimplement get logic or call a helper
                    return None # 暂时返回None，或者复制get_project的逻辑
                
                admin_client = self.get_admin_client()
                if not admin_client:
                    return None
                    
                update_query = admin_client.table("projects").update(update_data).eq("id", project_id)
                if user_id:
                    update_query = update_query.eq("user_id", user_id)
                response = update_query.execute()
                
                if response.data and len(response.data) > 0:
                    logger.info(f"项目更新成功: {project_id}")
                    return response.data[0]
                else:
                    return None
            except Exception as e:
                logger.error(f"项目更新出错: {str(e)}")
                return None

        import asyncio
        # 如果没有更新数据，我们应该返回当前项目，这需要 await calls
        # 但在 to_thread 里不能 await。
        # 策略：如果 update_data 为空，我们在外层处理，或者这里直接做一个 sync 的 get
        if name is None and description is None:
            return await self.get_project(project_id, user_id=user_id)
            
        return await asyncio.to_thread(_sync_update)
    
    async def delete_project(self, project_id: str) -> bool:
        """异步删除项目"""
        def _sync_delete():
            try:
                admin_client = self.get_admin_client()
                if not admin_client: return False
                    
                logger.info(f"删除项目 {project_id} 的相关数据")
                admin_client.table("prompt_history").delete().eq("project_id", project_id).execute()
                admin_client.table("prompts").delete().eq("project_id", project_id).execute()
                project_response = admin_client.table("projects").delete().eq("id", project_id).eq("user_id", user_id).execute() if user_id \
                    else admin_client.table("projects").delete().eq("id", project_id).execute()
                
                if project_response.data:
                    logger.info(f"项目删除成功: {project_id}")
                    return True
                else:
                    return False
            except Exception as e:
                logger.error(f"项目删除出错: {str(e)}")
                return False

        import asyncio
        return await asyncio.to_thread(_sync_delete)

    # 内部同步辅助方法，供 _sync_create 等调用
    def _get_current_user_sync(self) -> Dict[str, Any]:
        try:
            response = self.client.auth.get_user()
            if response and response.user:
                return {
                    "id": response.user.id,
                    "email": response.user.email,
                    "username": response.user.user_metadata.get("username") if response.user.user_metadata else None,
                    "created_at": response.user.created_at
                }
            return None
        except Exception:
            return None
    
    # 提示词相关操作 - 异步改造
    async def create_prompt(self, project_id: str, content: str, variables: Dict[str, str], user_id: str, is_public: bool = False) -> Dict[str, Any]:
        """异步创建新的提示词"""
        def _sync_create():
            try:
                # 准备提示词数据
                prompt_data = {
                    "project_id": project_id,
                    "content": content,
                    "variables": variables,
                    "user_id": user_id,
                    "is_public": is_public,
                    "version": 1  # 初始版本号
                }
                
                # 使用管理员客户端插入数据，绕过RLS策略
                admin_client = self.get_admin_client()
                if not admin_client:
                    logger.error("无法获取管理员客户端，创建提示词失败")
                    return None
                
                # 执行插入
                response = admin_client.table("prompts").insert(prompt_data).execute()
                
                if response.data and len(response.data) > 0:
                    logger.info(f"提示词创建成功: {response.data[0]['id']}")
                    return response.data[0]
                else:
                    logger.error(f"提示词创建失败: 没有返回数据")
                    return None
                    
            except Exception as e:
                logger.error(f"提示词创建出错: {str(e)}")
                return None
        
        import asyncio
        return await asyncio.to_thread(_sync_create)
    
    async def get_project_prompts(self, project_id: str) -> List[Dict[str, Any]]:
        """异步获取项目的所有提示词"""
        def _sync_get():
            try:
                logger.debug(f"尝试获取项目 {project_id} 的提示词列表")
                
                try:
                    admin_client = self.get_admin_client()
                    if not admin_client:
                        return []
                    
                    response = admin_client.table("prompts").select("*").eq("project_id", project_id).execute()
                    
                    if response.data:
                        logger.info(f"找到 {len(response.data)} 个提示词属于项目 {project_id}")
                        return response.data
                    else:
                        return []
                except Exception as db_error:
                    logger.error(f"管理员客户端获取失败: {str(db_error)}")
                    logger.info("尝试使用普通客户端获取项目提示词...")
                    response = self.client.table("prompts").select("*").eq("project_id", project_id).execute()
                    return response.data if response.data else []
            except Exception as e:
                logger.error(f"获取项目提示词列表出错: {str(e)}")
                return []
        
        import asyncio
        return await asyncio.to_thread(_sync_get)
    
    async def get_prompt(self, prompt_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """异步获取提示词详情（提供 user_id 时附加归属过滤）"""
        def _sync_get():
            try:
                admin_client = self.get_admin_client()
                if not admin_client:
                    return None

                query = admin_client.table("prompts").select("*").eq("id", prompt_id)
                if user_id:
                    query = query.eq("user_id", user_id)
                response = query.execute()
                
                if response.data and len(response.data) > 0:
                    return response.data[0]
                else:
                    logger.error(f"提示词不存在或无权访问: {prompt_id}")
                    return None
            except Exception as e:
                logger.error(f"获取提示词详情出错: {str(e)}")
                return None
        
        import asyncio
        return await asyncio.to_thread(_sync_get)
    
    async def update_prompt(self, prompt_id: str, content: Optional[str] = None,
                     version: Optional[int] = None, variables: Optional[Dict] = None,
                     title: Optional[str] = None, description: Optional[str] = None,
                     is_public: Optional[bool] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
        """异步更新提示词（提供 user_id 时附加归属过滤，防止越权修改）"""
        def _update_sync():
            try:
                # 准备更新数据
                update_data = {}
                if content is not None:
                    update_data["content"] = content
                if version is not None:
                    update_data["version"] = version
                if variables is not None:
                    update_data["variables"] = variables
                if title is not None:
                    update_data["title"] = title
                if description is not None:
                    update_data["description"] = description
                if is_public is not None:
                    update_data["is_public"] = is_public
                
                if not update_data:
                    # Sync version of strict get
                    return None # placeholder, handling empty update outside or via strict get
                
                admin_client = self.get_admin_client()
                if not admin_client:
                    return None
                    
                update_query = admin_client.table("prompts").update(update_data).eq("id", prompt_id)
                if user_id:
                    update_query = update_query.eq("user_id", user_id)
                response = update_query.execute()
                
                if response.data and len(response.data) > 0:
                    logger.info(f"提示词更新成功: {prompt_id}")
                    return response.data[0]
                else:
                    return None
            except Exception as e:
                logger.error(f"提示词更新出错: {str(e)}")
                return None
        
        import asyncio
        # Handle empty update externally or by a separate async get call if needed
        if all(x is None for x in [content, version, variables, title, description, is_public]):
            return await self.get_prompt(prompt_id, user_id=user_id)

        return await asyncio.to_thread(_update_sync)
    
    async def delete_prompt(self, prompt_id: str, user_id: Optional[str] = None) -> bool:
        """异步删除提示词（提供 user_id 时附加归属过滤，防止越权删除）"""
        def _sync_delete():
            try:
                admin_client = self.get_admin_client()
                if not admin_client:
                    return False

                delete_query = admin_client.table("prompts").delete().eq("id", prompt_id)
                if user_id:
                    delete_query = delete_query.eq("user_id", user_id)
                response = delete_query.execute()
                
                if response.data:
                    logger.info(f"提示词删除成功: {prompt_id}")
                    return True
                else:
                    return False
            except Exception as e:
                logger.error(f"提示词删除出错: {str(e)}")
                return False
        
        import asyncio
        return await asyncio.to_thread(_sync_delete)
    
    # 用户相关操作 - 异步改造
    async def get_user(self, user_id: str) -> Dict[str, Any]:
        """异步获取用户信息"""
        def _sync_get():
            try:
                # 获取用户数据需要管理员权限
                admin_client = self.get_admin_client()
                response = admin_client.auth.admin.get_user_by_id(user_id)
                
                if response and response.user:
                    user_data = {
                        "id": response.user.id,
                        "email": response.user.email,
                        "username": response.user.user_metadata.get("username") if response.user.user_metadata else None,
                        "created_at": response.user.created_at
                    }
                    return user_data
                else:
                    logger.error(f"用户不存在: {user_id}")
                    return None
            except Exception as e:
                logger.error(f"获取用户信息出错: {str(e)}")
                return None
        
        import asyncio
        return await asyncio.to_thread(_sync_get)
    
    async def get_current_user(self) -> Dict[str, Any]:
        """异步获取当前登录用户信息"""
        import asyncio
        return await asyncio.to_thread(self._get_current_user_sync)

    async def get_user_projects(self, user_id: str) -> List[Dict[str, Any]]:
        """异步获取特定用户的项目列表"""
        def _sync_get():
            if not user_id:
                logger.error("获取用户项目列表失败: 用户ID为空")
                return []
                
            try:
                # 构建查询，只获取该用户拥有的项目
                query = self.client.table("projects").select("*").eq("user_id", user_id)
                response = query.order("created_at", desc=True).execute()
                
                if response.data:
                    logger.debug(f"找到 {len(response.data)} 个项目属于用户 {user_id}")
                    return response.data
                else:
                    logger.debug(f"用户 {user_id} 没有任何项目")
                    return []
            except Exception as e:
                logger.error(f"获取用户项目列表出错: {str(e)}")
                return []
        
        import asyncio
        return await asyncio.to_thread(_sync_get)

    async def get_latest_prompt_version(self, project_id: str) -> Optional[int]:
        """异步获取项目的最新提示词版本号"""
        def _sync_get():
            try:
                admin_client = self.get_admin_client()
                if not admin_client:
                    return None
                    
                response = admin_client.table("prompt_history") \
                    .select("version") \
                    .eq("project_id", project_id) \
                    .order("version", desc=True) \
                    .limit(1) \
                    .execute()
                    
                if response.data and len(response.data) > 0:
                    return response.data[0]["version"]
                return None
            except Exception as e:
                logger.error(f"获取最新版本号失败: {str(e)}")
                return None

        import asyncio
        return await asyncio.to_thread(_sync_get)
            
    async def create_prompt_history(self, project_id: str, system_prompt: str, version: int,
                            user_id: str, change_summary: str, variables: Dict = None,
                            user_prompt: str = "", content: str = None) -> Dict[str, Any]:
        """异步创建提示词历史记录"""
        def _sync_create():
            try:
                # 向后兼容：如果提供了 content 参数，使用它作为 system_prompt
                # 注意：不能修改外部变量，所以这里作为局部变量
                sp = content if content is not None else system_prompt
                
                # 准备历史记录数据
                history_data = {
                    "project_id": project_id,
                    "system_prompt": sp,
                    "user_prompt": user_prompt or "",
                    "version": version,
                    "user_id": user_id,
                    "change_summary": change_summary,
                    "variables": variables or {}  # 如果没有提供变量信息，使用空字典
                }
                
                admin_client = self.get_admin_client()
                if not admin_client:
                    return None
                    
                response = admin_client.table("prompt_history").insert(history_data).execute()
                
                if response.data and len(response.data) > 0:
                    logger.info(f"提示词历史记录创建成功: {response.data[0]['id']}")
                    return response.data[0]
                else:
                    return None
            except Exception as e:
                logger.error(f"创建提示词历史记录失败: {str(e)}")
                return None

        import asyncio
        return await asyncio.to_thread(_sync_create)

    async def get_prompt_history(self, project_id: str) -> List[Dict[str, Any]]:
        """异步获取项目的提示词历史记录"""
        def _sync_get():
            try:
                admin_client = self.get_admin_client()
                if not admin_client:
                    return []
                    
                response = admin_client.table("prompt_history") \
                    .select("*") \
                    .eq("project_id", project_id) \
                    .order("version", desc=True) \
                    .execute()
                    
                if response.data:
                    return response.data
                return []
            except Exception as e:
                logger.error(f"获取提示词历史记录失败: {str(e)}")
                return []

        import asyncio
        return await asyncio.to_thread(_sync_get)
            
    async def get_prompt_history_by_id(self, history_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """异步根据ID获取单条历史记录（提供 user_id 时附加归属过滤）"""
        def _sync_get():
            try:
                admin_client = self.get_admin_client()
                if not admin_client:
                    return None

                query = admin_client.table("prompt_history") \
                    .select("*") \
                    .eq("id", history_id)
                if user_id:
                    query = query.eq("user_id", user_id)
                response = query.execute()
                    
                if response.data and len(response.data) > 0:
                    return response.data[0]
                return None
            except Exception as e:
                logger.error(f"获取历史记录失败: {str(e)}")
                return None

        import asyncio
        return await asyncio.to_thread(_sync_get)
            
    async def update_prompt_history(self, history_id: str, content: Optional[str] = None,
                            change_summary: Optional[str] = None, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """异步更新历史记录（提供 user_id 时附加归属过滤，防止越权修改）"""
        def _sync_update():
            try:
                update_data = {}
                if content is not None:
                    update_data["content"] = content
                if change_summary is not None:
                    update_data["change_summary"] = change_summary
                    
                if not update_data:
                    # 我们无法在 sync wrapper 里 await self.get...
                    # 简单返回 None，让调用者必须提供数据
                    return None
                    
                admin_client = self.get_admin_client()
                if not admin_client:
                    return None
                    
                update_query = admin_client.table("prompt_history") \
                    .update(update_data) \
                    .eq("id", history_id)
                if user_id:
                    update_query = update_query.eq("user_id", user_id)
                response = update_query.execute()
                    
                if response.data and len(response.data) > 0:
                    logger.info(f"历史记录更新成功: {history_id}")
                    return response.data[0]
                return None
            except Exception as e:
                logger.error(f"更新历史记录失败: {str(e)}")
                return None

        import asyncio
        if content is None and change_summary is None:
            return await self.get_prompt_history_by_id(history_id, user_id=user_id)
            
        return await asyncio.to_thread(_sync_update)
            
    async def delete_prompt_history(self, history_id: str, user_id: Optional[str] = None) -> bool:
        """异步删除历史记录（提供 user_id 时附加归属过滤，防止越权删除）"""
        def _sync_delete():
            try:
                admin_client = self.get_admin_client()
                if not admin_client:
                    return False
                delete_query = admin_client.table("prompt_history").delete().eq("id", history_id)
                if user_id:
                    delete_query = delete_query.eq("user_id", user_id)
                response = delete_query.execute()
                if response and getattr(response, 'data', None):
                     return True
                return True 
            except Exception as e:
                logger.error(f"删除历史记录失败: {str(e)}")
                return False

        import asyncio
        return await asyncio.to_thread(_sync_delete)

    async def count_prompt_versions(self, prompt_id: str) -> int:
        """异步获取提示词历史版本总数"""
        def _sync_count():
            try:
                # 使用管理员客户端查询，绕过RLS策略
                admin_client = self.get_admin_client()
                if not admin_client:
                    logger.error("无法获取管理员客户端")
                    return 0
                    
                response = admin_client.table("prompt_history") \
                    .select("id", count="exact") \
                    .eq("prompt_id", prompt_id) \
                    .execute()
                    
                return response.count or 0
                    
            except Exception as e:
                logger.error(f"获取提示词历史版本总数失败: {str(e)}")
                return 0
        
        import asyncio
        return await asyncio.to_thread(_sync_count)
            
    async def get_prompt_versions(
        self,
        prompt_id: str,
        limit: int = 10,
        offset: int = 0,
        sort_by: str = "version",
        sort_order: str = "desc"
    ) -> List[Dict[str, Any]]:
        """异步获取提示词历史版本列表"""
        def _sync_get():
            try:
                # 使用管理员客户端查询，绕过RLS策略
                admin_client = self.get_admin_client()
                if not admin_client:
                    logger.error("无法获取管理员客户端")
                    return []
                
                # 构建查询
                query = admin_client.table("prompt_history") \
                    .select("*") \
                    .eq("prompt_id", prompt_id)
                    
                # 添加排序
                query = query.order(sort_by, desc=(sort_order == "desc"))
                
                # 添加分页
                query = query.range(offset, offset + limit - 1)
                
                # 执行查询
                response = query.execute()
                
                if response.data:
                    # 格式化返回数据
                    # Handle missing keys gracefully if schema differs
                    return [{
                        "id": version["id"],
                        "version": version.get("version"),
                        "content": version.get("content") or version.get("system_prompt"),
                        "variables": version.get("variables", {}).get("variables", []) if isinstance(version.get("variables"), dict) else [],
                        "change_summary": version.get("change_summary"),
                        "created_at": version.get("created_at"),
                        "user_id": version.get("user_id")
                    } for version in response.data]
                    
                return []
                
            except Exception as e:
                logger.error(f"获取提示词历史版本列表失败: {str(e)}")
                return []
        
        import asyncio
        return await asyncio.to_thread(_sync_get)



# 创建单例实例
supabase_db = SupabaseDB() 