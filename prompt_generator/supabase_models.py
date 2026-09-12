"""
Supabase数据库模型定义
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

# 用户相关模型
class UserCreate(BaseModel):
    """创建用户的请求模型"""
    email: str
    password: str
    username: Optional[str] = None

class UserResponse(BaseModel):
    """用户信息响应模型"""
    id: str
    email: str
    username: Optional[str] = None
    created_at: datetime

class UserLogin(BaseModel):
    """用户登录请求模型"""
    email: str
    password: str

class TokenResponse(BaseModel):
    """令牌响应模型"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: Optional[str] = None
    user: UserResponse

class UserCreatedResponse(BaseModel):
    """用户创建响应模型，不包含令牌"""
    message: str
    user: UserResponse

# 项目相关模型
class ProjectCreate(BaseModel):
    """创建项目请求模型"""
    name: str
    description: Optional[str] = None

class ProjectResponse(BaseModel):
    """项目信息响应模型"""
    id: str
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    user_id: str

class ProjectUpdate(BaseModel):
    """更新项目请求模型"""
    name: Optional[str] = None
    description: Optional[str] = None

# 提示词相关模型
class PromptCreate(BaseModel):
    """创建提示词请求模型"""
    project_id: str
    content: str
    version: str
    variables: Optional[Dict[str, Any]] = None

class PromptResponse(BaseModel):
    """提示词信息响应模型"""
    id: str
    project_id: str
    content: str
    version: str
    variables: Optional[Dict[str, Any]] = None
    created_at: datetime
    user_id: str

class PromptUpdate(BaseModel):
    """更新提示词请求模型"""
    content: Optional[str] = None
    version: Optional[str] = None
    variables: Optional[Dict[str, Any]] = None

# 数据库SQL脚本
SUPABASE_SCHEMA_SQL = """
-- 启用必要的扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 创建项目表
CREATE TABLE IF NOT EXISTS projects (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL CHECK(char_length(name) <= 50),
  description TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL
);

-- 创建提示词历史表 (支持 system prompt 和 user prompt)
CREATE TABLE IF NOT EXISTS prompt_history (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE NOT NULL,
  version INTEGER NOT NULL DEFAULT 1,
  system_prompt TEXT NOT NULL DEFAULT '',
  user_prompt TEXT DEFAULT '',
  variables JSONB,
  change_summary TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL
);

-- 设置行级安全策略
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE prompts ENABLE ROW LEVEL SECURITY;

-- 创建项目的访问策略
CREATE POLICY "用户可以访问自己的项目" ON projects
  FOR ALL USING (auth.uid() = user_id);

-- 创建提示词的访问策略
CREATE POLICY "用户可以访问自己的提示词" ON prompts
  FOR ALL USING (auth.uid() = user_id);

-- 创建自动更新时间的触发器函数
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 为项目表添加更新时间触发器
CREATE TRIGGER set_updated_at
BEFORE UPDATE ON projects
FOR EACH ROW
EXECUTE FUNCTION update_updated_at();
""" 