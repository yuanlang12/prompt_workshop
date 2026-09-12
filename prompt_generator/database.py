import sqlite3
import json
import os
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path="prompts.db"):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 创建项目表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL CHECK(length(name) <= 50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建提示词表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS prompts (
                    id TEXT PRIMARY KEY,
                    project_id TEXT,
                    version TEXT NOT NULL,
                    content TEXT NOT NULL,
                    variables TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                )
            ''')
            
            conn.commit()

    def create_project(self, name, user_id):
        """创建项目（添加用户ID支持）"""
        project_id = str(uuid.uuid4())
        created_at = datetime.now().isoformat()
        
        with self.get_connection() as conn:
            query = """
            INSERT INTO projects (id, name, created_at, user_id)
            VALUES (?, ?, ?, ?)
            """
            conn.execute(query, (project_id, name, created_at, user_id))
            conn.commit()
        
        return {"id": project_id, "name": name, "created_at": created_at}

    def get_projects(self) -> list:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, created_at FROM projects ORDER BY created_at DESC")
            return [
                {
                    "id": row[0],
                    "name": row[1],
                    "created_at": row[2]
                }
                for row in cursor.fetchall()
            ]

    def create_prompt(self, project_id: str, content: str, variables: list) -> dict:
        """创建提示词并存储到数据库
        
        Args:
            project_id: 项目ID
            content: 提示词内容
            variables: 变量列表
            
        Returns:
            包含创建的提示词信息的字典
        """
        logger = logging.getLogger(__name__)
        
        # 确保 content 是有效的 UTF-8 编码字符串
        if not isinstance(content, str):
            logger.warning(f"Content is not a string: {type(content)}")
            content = str(content)
        
        # 尝试修复内容中的编码问题
        try:
            # 如果内容已经是损坏的编码（包含\x转义字符），尝试修复
            if '\\x' in content:
                logger.debug("检测到可能的编码问题，尝试修复内容编码")
                try:
                    # 方法1: 尝试latin1到utf8的转换
                    fixed_content = content.encode('latin1').decode('utf-8', errors='replace')
                    if not any(c == '\ufffd' for c in fixed_content):  # 检查是否有替换字符
                        content = fixed_content
                    else:
                        # 方法2: 尝试修复转义序列
                        import re
                        def replace_hex(match):
                            try:
                                return bytes.fromhex(match.group(1)).decode('utf-8')
                            except:
                                return '?'
                        content = re.sub(r'\\x([0-9a-fA-F]{2})', replace_hex, content)
                except Exception as e:
                    logger.error(f"修复内容编码失败: {str(e)}")
        except Exception as e:
            logger.error(f"处理编码问题时出错: {str(e)}")
        
        # 确保 variables 中的每个元素都是有效的字符串
        cleaned_variables = []
        for v in variables:
            if isinstance(v, str):
                # 对变量进行相同的编码修复
                if '\\x' in v:
                    try:
                        fixed_v = v.encode('latin1').decode('utf-8', errors='replace')
                        if not any(c == '\ufffd' for c in fixed_v):
                            v = fixed_v
                    except Exception as e:
                        logger.error(f"修复变量编码失败: {str(e)}")
                cleaned_variables.append(v)
            else:
                cleaned_variables.append(str(v))
        
        variables = cleaned_variables
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 获取当前项目的最新版本号
            cursor.execute(
                "SELECT version FROM prompts WHERE project_id = ? ORDER BY created_at DESC LIMIT 1",
                (project_id,)
            )
            last_version = cursor.fetchone()
            
            # 计算新版本号
            if last_version:
                version_num = int(last_version[0][1:]) + 1
                version = f"v{version_num}"
            else:
                version = "v1"
            
            prompt_id = str(uuid.uuid4())
            cursor.execute(
                "INSERT INTO prompts (id, project_id, version, content, variables) VALUES (?, ?, ?, ?, ?)",
                (prompt_id, project_id, version, content, json.dumps(variables))
            )
            conn.commit()
            
            cursor.execute(
                "SELECT id, version, content, variables, created_at FROM prompts WHERE id = ?",
                (prompt_id,)
            )
            row = cursor.fetchone()
            return {
                "id": row[0],
                "version": row[1],
                "content": row[2],
                "variables": json.loads(row[3]),
                "created_at": row[4]
            }

    def get_project_prompts(self, project_id: str) -> list:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, version, content, variables, created_at FROM prompts WHERE project_id = ? ORDER BY created_at DESC",
                (project_id,)
            )
            return [
                {
                    "id": row[0],
                    "version": row[1],
                    "content": row[2],
                    "variables": json.loads(row[3]),
                    "created_at": row[4]
                }
                for row in cursor.fetchall()
            ]

    def get_prompt(self, prompt_id: str) -> dict:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, version, content, variables, created_at FROM prompts WHERE id = ?",
                (prompt_id,)
            )
            row = cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "version": row[1],
                    "content": row[2],
                    "variables": json.loads(row[3]),
                    "created_at": row[4]
                }
            return None 

    def update_prompt_variables(self, prompt_id: str, variables: list):
        """更新提示词的变量列表"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE prompts SET variables = ? WHERE id = ?",
                    (json.dumps(variables), prompt_id)
                )
                conn.commit()
                logger.debug(f"Updated variables for prompt {prompt_id}: {variables}")
        except Exception as e:
            logger.error(f"Failed to update variables for prompt {prompt_id}: {str(e)}")
            raise e

    def rename_project(self, project_id: str, new_name: str) -> dict:
        """重命名项目"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE projects SET name = ? WHERE id = ? RETURNING id, name, created_at",
                (new_name, project_id)
            )
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Project with id {project_id} not found")
            
            return {
                "id": row[0],
                "name": row[1],
                "created_at": row[2]
            } 

    def delete_project(self, project_id: str) -> None:
        """删除项目及其所有相关提示词

        Args:
            project_id: 项目ID

        Raises:
            ValueError: 如果项目不存在
        """
        try:
            with self.get_connection() as conn:
                # 检查项目是否存在
                cursor = conn.execute(
                    "SELECT id FROM projects WHERE id = ?",
                    (project_id,)
                )
                if not cursor.fetchone():
                    raise ValueError("项目不存在")

                # 删除项目相关的所有提示词
                conn.execute(
                    "DELETE FROM prompts WHERE project_id = ?",
                    (project_id,)
                )

                # 删除项目
                conn.execute(
                    "DELETE FROM projects WHERE id = ?",
                    (project_id,)
                )
        except Exception as e:
            logger.error(f"Error deleting project: {str(e)}")
            raise 

    def get_user(self, user_id):
        """获取用户信息"""
        with self.get_connection() as conn:
            query = "SELECT * FROM users WHERE id = ?"
            result = conn.execute(query, (user_id,)).fetchone()
            if not result:
                return None
            return dict(result)

    def get_user_by_authing_id(self, authing_id):
        """通过Authing ID获取用户"""
        with self.get_connection() as conn:
            query = "SELECT * FROM users WHERE authing_id = ?"
            result = conn.execute(query, (authing_id,)).fetchone()
            if not result:
                return None
            return dict(result)

    def create_user(self, id, authing_id, username, email, created_at):
        """创建新用户"""
        with self.get_connection() as conn:
            query = """
            INSERT INTO users (id, authing_id, username, email, created_at)
            VALUES (?, ?, ?, ?, ?)
            """
            conn.execute(query, (id, authing_id, username, email, created_at))
            conn.commit()
            return {"id": id, "username": username}

    def get_user_projects(self, user_id):
        """获取用户的项目列表"""
        with self.get_connection() as conn:
            query = "SELECT * FROM projects WHERE user_id = ? ORDER BY created_at DESC"
            result = conn.execute(query, (user_id,)).fetchall()
            return [dict(row) for row in result] 