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
        if supabase is None:
            self.client = init_supabase()
            if self.client is None:
                logger.error("Supabase客户端初始化失败")
                raise Exception("Supabase客户端初始化失败")
        else:
            self.client = supabase
        
        # 添加错误信息属性
        self.last_error = None
    
    def get_admin_client(self):
        """获取管理员权限的Supabase客户端，用于管理员操作"""
        admin_client = get_supabase_admin_client()
        if admin_client is None:
            logger.error("无法获取Supabase管理员客户端")
            raise Exception("无法获取Supabase管理员客户端")
        return admin_client
    
    # 项目相关操作
    def create_project(self, name: str, description: Optional[str] = None, user_id: str = None) -> Dict[str, Any]:
        """
        创建新项目
        
        Args:
            name: 项目名称
            description: 项目描述（可选）
            user_id: 用户ID（可选，如果不提供则使用当前登录用户）
            
        Returns:
            项目信息字典
        """
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
                current_user = self.get_current_user()
                if current_user:
                    logger.debug(f"当前用户ID: {current_user['id']}")
                    project_data["user_id"] = current_user["id"]
                else:
                    logger.error("创建项目失败: 未登录或无法获取当前用户")
                    return None
            
            logger.debug(f"准备插入项目数据: {project_data}")
            
            # 确保user_id字段存在
            if "user_id" not in project_data or not project_data["user_id"]:
                logger.error("创建项目失败: 用户ID为空")
                return None
                
            # 使用管理员客户端插入项目数据，绕过RLS策略
            try:
                # 获取管理员客户端
                admin_client = self.get_admin_client()
                if not admin_client:
                    logger.error("无法获取管理员客户端，创建项目失败")
                    self.last_error = "无法获取管理员客户端"
                    return None
                
                # 使用管理员客户端插入数据
                logger.debug("使用管理员客户端创建项目，绕过RLS策略")
                response = admin_client.table("projects").insert(project_data).execute()
                
                if response.data and len(response.data) > 0:
                    logger.info(f"项目创建成功: {response.data[0]['id']}")
                    return response.data[0]
                else:
                    logger.error(f"项目创建失败: 没有返回数据，响应: {response}")
                    return None
            except Exception as db_error:
                # 更详细地记录数据库错误
                logger.error(f"数据库插入错误: {str(db_error)}")
                # 记录错误信息到last_error属性
                self.last_error = str(db_error)
                # 检查是否是外键或约束错误
                error_str = str(db_error).lower()
                if "foreign key" in error_str or "constraint" in error_str:
                    logger.error("可能是外键约束错误，检查用户ID是否有效")
                    self.last_error = "外键约束错误，检查用户ID是否有效"
                elif "permission" in error_str or "denied" in error_str:
                    logger.error("可能是权限错误，检查数据库权限设置")
                    self.last_error = "权限错误，检查数据库权限设置"
                return None
        except Exception as e:
            logger.error(f"项目创建出错: {str(e)}")
            import traceback
            logger.error(f"异常堆栈: {traceback.format_exc()}")
            # 记录错误信息到last_error属性
            self.last_error = str(e)
            return None
    
    def get_projects(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取项目列表
        
        Args:
            user_id: 用户ID（可选，如果不提供则获取当前用户的项目）
            
        Returns:
            项目列表
        """
        try:
            if not user_id:
                logger.warning("获取项目列表: 未提供用户ID")
                return []
                
            logger.debug(f"获取用户 {user_id} 的项目列表")
            
            # 使用管理员客户端查询，绕过RLS策略
            try:
                # 获取管理员客户端
                admin_client = self.get_admin_client()
                if not admin_client:
                    logger.error("无法获取管理员客户端，获取项目列表失败")
                    return []
                
                # 构建查询
                query = admin_client.table("projects").select("*").eq("user_id", user_id)
                
                # 执行查询
                response = query.order("created_at", desc=True).execute()
                
                logger.debug(f"获取项目列表响应: data={response.data} count={response.count}")
                
                if response.data:
                    logger.info(f"找到 {len(response.data)} 个项目属于用户 {user_id}")
                    return response.data
                else:
                    logger.warning(f"用户 {user_id} 没有任何项目")
                    return []
            except Exception as db_error:
                logger.error(f"使用管理员客户端获取项目列表出错: {str(db_error)}")
                # 尝试使用普通客户端作为备选方案
                logger.info("尝试使用普通客户端获取项目列表...")
                query = self.client.table("projects").select("*").eq("user_id", user_id)
                response = query.order("created_at", desc=True).execute()
                
                if response.data:
                    logger.info(f"使用普通客户端找到 {len(response.data)} 个项目")
                    return response.data
                else:
                    return []
        except Exception as e:
            logger.error(f"获取项目列表出错: {str(e)}")
            return []
    
    def get_project(self, project_id: str) -> Dict[str, Any]:
        """
        获取项目详情
        
        Args:
            project_id: 项目ID
            
        Returns:
            项目信息字典
        """
        try:
            logger.debug(f"尝试获取项目: {project_id}")
            
            # 使用管理员客户端获取项目详情，绕过RLS策略
            admin_client = self.get_admin_client()
            if not admin_client:
                logger.error("无法获取管理员客户端，获取项目详情失败")
                return None
                
            response = admin_client.table("projects").select("*").eq("id", project_id).execute()
            
            logger.debug(f"获取项目响应: {response}")
            
            if response.data and len(response.data) > 0:
                project = response.data[0]
                logger.debug(f"成功获取项目: ID={project_id}, 用户ID={project.get('user_id')}, 名称={project.get('name')}")
                return project
            else:
                logger.error(f"项目不存在: {project_id}")
                return None
        except Exception as e:
            logger.error(f"获取项目详情出错: {str(e)}")
            return None
    
    def update_project(self, project_id: str, name: Optional[str] = None, 
                      description: Optional[str] = None) -> Dict[str, Any]:
        """
        更新项目信息
        
        Args:
            project_id: 项目ID
            name: 新项目名称（可选）
            description: 新项目描述（可选）
            
        Returns:
            更新后的项目信息
        """
        try:
            # 准备更新数据
            update_data = {}
            if name is not None:
                update_data["name"] = name
            if description is not None:
                update_data["description"] = description
            
            # 如果没有要更新的数据，直接返回
            if not update_data:
                return self.get_project(project_id)
            
            # 获取管理员客户端
            admin_client = self.get_admin_client()
            if not admin_client:
                logger.error("无法获取管理员客户端，更新项目失败")
                return None
                
            # 使用管理员客户端执行更新
            response = admin_client.table("projects").update(update_data).eq("id", project_id).execute()
            
            if response.data and len(response.data) > 0:
                logger.info(f"项目更新成功: {project_id}")
                return response.data[0]
            else:
                logger.error(f"项目更新失败: {project_id}")
                return None
        except Exception as e:
            logger.error(f"项目更新出错: {str(e)}")
            return None
    
    def delete_project(self, project_id: str) -> bool:
        """
        删除项目及其相关的所有提示词和历史记录
        
        Args:
            project_id: 项目ID
            
        Returns:
            删除是否成功
        """
        try:
            # 获取管理员客户端
            admin_client = self.get_admin_client()
            if not admin_client:
                logger.error("无法获取管理员客户端")
                return False
                
            # 1. 先删除项目关联的所有提示词历史记录
            logger.info(f"删除项目 {project_id} 的所有提示词历史记录")
            history_response = admin_client.table("prompt_history").delete().eq("project_id", project_id).execute()
            
            # 2. 删除项目中的所有提示词
            logger.info(f"删除项目 {project_id} 的所有提示词")
            prompts_response = admin_client.table("prompts").delete().eq("project_id", project_id).execute()
            
            # 3. 最后删除项目本身
            logger.info(f"删除项目 {project_id}")
            project_response = admin_client.table("projects").delete().eq("id", project_id).execute()
            
            if project_response.data:
                logger.info(f"项目删除成功: {project_id}")
                logger.info(f"删除了 {len(history_response.data or [])} 条历史记录和 {len(prompts_response.data or [])} 条提示词")
                return True
            else:
                logger.error(f"项目删除失败: {project_id}")
                return False
        except Exception as e:
            logger.error(f"项目删除出错: {str(e)}")
            return False
    
    # 提示词相关操作
    def create_prompt(self, project_id: str, content: str, variables: Dict[str, str], user_id: str, is_public: bool = False) -> Dict[str, Any]:
        """创建新的提示词
        
        Args:
            project_id: 项目ID
            content: 提示词内容
            variables: 变量字典
            user_id: 用户ID
            is_public: 是否公开（默认为私有）
            
        Returns:
            提示词信息字典
        """
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
    
    def get_project_prompts(self, project_id: str) -> List[Dict[str, Any]]:
        """
        获取项目的所有提示词
        
        Args:
            project_id: 项目ID
            
        Returns:
            提示词列表
        """
        try:
            logger.debug(f"尝试获取项目 {project_id} 的提示词列表")
            
            # 使用管理员客户端查询，绕过RLS策略
            try:
                # 获取管理员客户端
                admin_client = self.get_admin_client()
                if not admin_client:
                    logger.error("无法获取管理员客户端，获取项目提示词列表失败")
                    return []
                
                # 构建查询
                response = admin_client.table("prompts").select("*").eq("project_id", project_id).execute()
                
                logger.debug(f"获取提示词列表响应: data={response.data} count={response.count}")
                
                if response.data:
                    logger.info(f"找到 {len(response.data)} 个提示词属于项目 {project_id}")
                    return response.data
                else:
                    logger.info(f"项目 {project_id} 没有任何提示词")
                    return []
            except Exception as db_error:
                logger.error(f"使用管理员客户端获取项目提示词出错: {str(db_error)}")
                # 尝试使用普通客户端作为备选方案
                logger.info("尝试使用普通客户端获取项目提示词...")
                response = self.client.table("prompts").select("*").eq("project_id", project_id).execute()
                
                if response.data:
                    logger.info(f"使用普通客户端找到 {len(response.data)} 个提示词")
                    return response.data
                else:
                    return []
        except Exception as e:
            logger.error(f"获取项目提示词列表出错: {str(e)}")
            return []
    
    def get_prompt(self, prompt_id: str) -> Dict[str, Any]:
        """
        获取提示词详情
        
        Args:
            prompt_id: 提示词ID
            
        Returns:
            提示词信息
        """
        try:
            # 使用管理员客户端查询，绕过RLS策略
            admin_client = self.get_admin_client()
            if not admin_client:
                logger.error("无法获取管理员客户端")
                return None
                
            response = admin_client.table("prompts").select("*").eq("id", prompt_id).execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]
            else:
                logger.error(f"提示词不存在或无权访问: {prompt_id}")
                return None
        except Exception as e:
            logger.error(f"获取提示词详情出错: {str(e)}")
            return None
    
    def update_prompt(self, prompt_id: str, content: Optional[str] = None,
                     version: Optional[int] = None, variables: Optional[Dict] = None,
                     title: Optional[str] = None, description: Optional[str] = None,
                     is_public: Optional[bool] = None) -> Dict[str, Any]:
        """
        更新提示词
        
        Args:
            prompt_id: 提示词ID
            content: 新内容（可选）
            version: 新版本（可选，整数类型）
            variables: 新变量（可选）
            title: 新标题（可选）
            description: 新描述（可选）
            is_public: 是否公开（可选）
            
        Returns:
            更新后的提示词信息
        """
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
            
            # 如果没有要更新的数据，直接返回
            if not update_data:
                return self.get_prompt(prompt_id)
            
            # 使用管理员客户端更新，绕过RLS策略
            admin_client = self.get_admin_client()
            if not admin_client:
                logger.error("无法获取管理员客户端")
                return None
                
            # 执行更新
            response = admin_client.table("prompts").update(update_data).eq("id", prompt_id).execute()
            
            if response.data and len(response.data) > 0:
                logger.info(f"提示词更新成功: {prompt_id}")
                return response.data[0]
            else:
                logger.error(f"提示词更新失败: {prompt_id}")
                return None
        except Exception as e:
            logger.error(f"提示词更新出错: {str(e)}")
            return None
    
    def delete_prompt(self, prompt_id: str) -> bool:
        """
        删除提示词
        
        Args:
            prompt_id: 提示词ID
            
        Returns:
            删除是否成功
        """
        try:
            # 使用管理员客户端删除，绕过RLS策略
            admin_client = self.get_admin_client()
            if not admin_client:
                logger.error("无法获取管理员客户端")
                return False
                
            response = admin_client.table("prompts").delete().eq("id", prompt_id).execute()
            
            if response.data:
                logger.info(f"提示词删除成功: {prompt_id}")
                return True
            else:
                logger.error(f"提示词删除失败: {prompt_id}")
                return False
        except Exception as e:
            logger.error(f"提示词删除出错: {str(e)}")
            return False
    
    # 用户相关操作
    def get_user(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            用户信息
        """
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
    
    def get_current_user(self) -> Dict[str, Any]:
        """
        获取当前登录用户信息
        
        Returns:
            当前用户信息，如果未登录则返回None
        """
        try:
            # 获取当前会话用户
            response = self.client.auth.get_user()
            
            if response and response.user:
                user_data = {
                    "id": response.user.id,
                    "email": response.user.email,
                    "username": response.user.user_metadata.get("username") if response.user.user_metadata else None,
                    "created_at": response.user.created_at
                }
                return user_data
            else:
                logger.warning("当前没有登录用户")
                return None
        except Exception as e:
            logger.error(f"获取当前用户信息出错: {str(e)}")
            return None

    def get_user_projects(self, user_id: str) -> List[Dict[str, Any]]:
        """
        获取特定用户的项目列表
        
        Args:
            user_id: 用户ID，必须提供
            
        Returns:
            项目列表
        """
        if not user_id:
            logger.error("获取用户项目列表失败: 用户ID为空")
            return []
            
        try:
            # 构建查询，只获取该用户拥有的项目
            query = self.client.table("projects").select("*").eq("user_id", user_id)
            
            # 执行查询
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

    def get_latest_prompt_version(self, project_id: str) -> Optional[int]:
        """获取项目的最新提示词版本号
        
        Args:
            project_id: 项目ID
            
        Returns:
            最新版本号，如果没有历史记录则返回None
        """
        try:
            # 使用管理员客户端查询
            admin_client = self.get_admin_client()
            if not admin_client:
                logger.error("无法获取管理员客户端")
                return None
                
            # 查询最新版本
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
            
    def create_prompt_history(self, project_id: str, system_prompt: str, version: int,
                            user_id: str, change_summary: str, variables: Dict = None,
                            user_prompt: str = "", content: str = None) -> Dict[str, Any]:
        """创建提示词历史记录
        
        Args:
            project_id: 项目ID
            system_prompt: System Prompt 内容
            version: 版本号
            user_id: 用户ID
            change_summary: 变更说明
            variables: 变量信息（可选，默认为空字典）
            user_prompt: User Prompt 内容（可选，默认为空）
            content: 向后兼容参数，如果提供则使用它作为 system_prompt
            
        Returns:
            创建的历史记录
        """
        try:
            # 向后兼容：如果提供了 content 参数，使用它作为 system_prompt
            if content is not None:
                system_prompt = content
            
            # 准备历史记录数据
            history_data = {
                "project_id": project_id,
                "system_prompt": system_prompt,
                "user_prompt": user_prompt or "",
                "version": version,
                "user_id": user_id,
                "change_summary": change_summary,
                "variables": variables or {}  # 如果没有提供变量信息，使用空字典
            }
            
            # 使用管理员客户端插入数据
            admin_client = self.get_admin_client()
            if not admin_client:
                logger.error("无法获取管理员客户端")
                return None
                
            # 执行插入
            response = admin_client.table("prompt_history").insert(history_data).execute()
            
            if response.data and len(response.data) > 0:
                logger.info(f"提示词历史记录创建成功: {response.data[0]['id']}")
                return response.data[0]
            else:
                logger.error("提示词历史记录创建失败: 没有返回数据")
                return None
                
        except Exception as e:
            logger.error(f"创建提示词历史记录失败: {str(e)}")
            return None

    def get_prompt_history(self, project_id: str) -> List[Dict[str, Any]]:
        """获取项目的提示词历史记录
        
        Args:
            project_id: 项目ID
            
        Returns:
            历史记录列表，按版本号降序排序
        """
        try:
            # 使用管理员客户端查询
            admin_client = self.get_admin_client()
            if not admin_client:
                logger.error("无法获取管理员客户端")
                return []
                
            # 查询历史记录
            response = admin_client.table("prompt_history") \
                .select("*") \
                .eq("project_id", project_id) \
                .order("version", desc=True) \
                .execute()
                
            if response.data:
                logger.info(f"找到 {len(response.data)} 条历史记录")
                return response.data
            return []
            
        except Exception as e:
            logger.error(f"获取提示词历史记录失败: {str(e)}")
            return []
            
    def get_prompt_history_by_id(self, history_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取单条历史记录
        
        Args:
            history_id: 历史记录ID
            
        Returns:
            历史记录信息，如果不存在则返回None
        """
        try:
            # 使用管理员客户端查询
            admin_client = self.get_admin_client()
            if not admin_client:
                logger.error("无法获取管理员客户端")
                return None
                
            # 查询单条记录
            response = admin_client.table("prompt_history") \
                .select("*") \
                .eq("id", history_id) \
                .execute()
                
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
            
        except Exception as e:
            logger.error(f"获取历史记录失败: {str(e)}")
            return None
            
    def update_prompt_history(self, history_id: str, content: Optional[str] = None,
                            change_summary: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """更新历史记录
        
        Args:
            history_id: 历史记录ID
            content: 新的提示词内容（可选）
            change_summary: 新的变更说明（可选）
            
        Returns:
            更新后的历史记录，如果失败则返回None
        """
        try:
            # 准备更新数据
            update_data = {}
            if content is not None:
                update_data["content"] = content
            if change_summary is not None:
                update_data["change_summary"] = change_summary
                
            if not update_data:
                logger.warning("没有需要更新的数据")
                return self.get_prompt_history_by_id(history_id)
                
            # 使用管理员客户端更新
            admin_client = self.get_admin_client()
            if not admin_client:
                logger.error("无法获取管理员客户端")
                return None
                
            # 执行更新
            response = admin_client.table("prompt_history") \
                .update(update_data) \
                .eq("id", history_id) \
                .execute()
                
            if response.data and len(response.data) > 0:
                logger.info(f"历史记录更新成功: {history_id}")
                return response.data[0]
            return None
            
        except Exception as e:
            logger.error(f"更新历史记录失败: {str(e)}")
            return None
            
    def delete_prompt_history(self, history_id: str) -> bool:
        """删除历史记录
        
        Args:
            history_id: 历史记录ID
            
        Returns:
            是否删除成功
        """
        try:
            # 使用管理员客户端删除
            admin_client = self.get_admin_client()
            if not admin_client:
                logger.error("无法获取管理员客户端")
                return False
                
            # 执行删除
            response = admin_client.table("prompt_history") \
                .delete() \
                .eq("id", history_id) \
                .execute()
                
            if response.data:
                logger.info(f"历史记录删除成功: {history_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"删除历史记录失败: {str(e)}")
            return False

    def count_prompt_versions(self, prompt_id: str) -> int:
        """获取提示词历史版本总数
        
        Args:
            prompt_id: 提示词ID
            
        Returns:
            历史版本总数
        """
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
            
    def get_prompt_versions(
        self,
        prompt_id: str,
        limit: int = 10,
        offset: int = 0,
        sort_by: str = "version",
        sort_order: str = "desc"
    ) -> List[Dict[str, Any]]:
        """获取提示词历史版本列表
        
        Args:
            prompt_id: 提示词ID
            limit: 每页数量
            offset: 偏移量
            sort_by: 排序字段
            sort_order: 排序方向
            
        Returns:
            历史版本列表
        """
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
                return [{
                    "id": version["id"],
                    "version": version["version"],
                    "content": version["content"],
                    "variables": version["variables"].get("variables", []) if version["variables"] else [],
                    "change_summary": version["change_summary"],
                    "created_at": version["created_at"],
                    "user_id": version["user_id"]
                } for version in response.data]
                
            return []
            
        except Exception as e:
            logger.error(f"获取提示词历史版本列表失败: {str(e)}")
            return []


# 创建单例实例
supabase_db = SupabaseDB() 