# 首先导入monkeypatch模块，修复uuid问题
# 尝试多种方法检测Vercel环境
import os
import sys
import datetime

# 检查是否在Vercel环境中（多种方式检测）
is_vercel = False
# 方法1: 检查VERCEL环境变量
if os.environ.get('VERCEL', False):
    is_vercel = True
# 方法2: 检查VERCEL_REGION环境变量 (Vercel通常会设置这个)
elif os.environ.get('VERCEL_REGION', False):
    is_vercel = True
# 方法3: 检查路径是否包含典型的Vercel路径特征
elif '/var/task/' in sys.path or any('vercel' in path.lower() for path in sys.path):
    is_vercel = True

# 根据环境决定是否使用monkeypatch
if is_vercel:
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import monkeypatch
        print("在Vercel环境中启用了uuid monkeypatch")
    except ImportError as e:
        print(f"警告: 无法导入monkeypatch模块: {e}")
else:
    print("在本地环境中运行，不需要uuid monkeypatch")

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
import re
from pydantic import BaseModel, constr, Field
from typing import Optional, List, Dict, Set, Union
import logging
import os
import json
from config.settings import API_KEY, MODEL_NAME, API_URL
import aiohttp
from aiohttp import ClientTimeout
from database import Database
import asyncio
import socket
import time
from fastapi import Depends
from fastapi.responses import RedirectResponse
from auth_routes import router as auth_router
from supabase_auth import SupabaseAuthService
from supabase_client import supabase
from supabase_models import UserResponse as UserInfo
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
# 导入Supabase数据库工具类
from supabase_db import SupabaseDB, supabase_db
from auth_utils import error_response, success_response, require_auth
from auth import get_current_user  # 使用 auth.py 中的版本，会抛出 HTTPException
from pydantic import validator
# 导入项目操作工具函数
from project_operations import rename_project, delete_project_with_history

# 导入环境变量
from config.settings import AVAILABLE_MODELS

# 创建用于依赖注入的Bearer token处理工具
security = HTTPBearer(auto_error=False)

# 设置基础路径
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# 配置日志（生产环境默认INFO，本地默认DEBUG，可通过环境变量LOG_LEVEL覆盖）
default_level_name = 'INFO' if is_vercel else 'DEBUG'
level_name = os.getenv('LOG_LEVEL', default_level_name).upper()
level_value = getattr(logging, level_name, logging.INFO)
logging.basicConfig(
    level=level_value,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 初始化数据库
# 注意：目前系统正从SQLite迁移到Supabase，所以同时使用两个数据库。
# 新的API端点应使用supabase_db，老的端点仍然使用SQLite数据库。
db = Database(os.path.join(BASE_DIR, "prompts.db"))

# 创建认证服务实例
auth_service = SupabaseAuthService()

app = FastAPI()

# 添加静态文件服务
static_path = os.path.join(BASE_DIR, "static")
app.mount("/static", StaticFiles(directory=static_path), name="static")

# 设置模板目录
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# CORS 跨域配置：默认仅同源（不添加 CORS 头）。
# 如需允许跨域调用 API（例如前后端分开部署），设置环境变量 ALLOWED_ORIGINS，
# 多个来源用英文逗号分隔，或设置为 * 允许所有来源（不推荐生产使用）
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "").strip()
if ALLOWED_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in ALLOWED_ORIGINS.split(",") if o.strip()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# 缓存 metaprompt（原文引自 Anthropic 公开的 Metaprompt，见 docs/prompts_attribution.md）
with open(os.path.join(BASE_DIR, "config", "prompts", "metaprompt.txt"), "r", encoding="utf-8") as f:
    CACHED_METAPROMPT = f.read()

# 缓存 improveprompt
with open(os.path.join(BASE_DIR, "config", "prompts", "improveprompt.txt"), "r", encoding="utf-8") as f:
    CACHED_IMPROVEPROMPT = f.read()

# 缓存 revise_plan_prompt
with open(os.path.join(BASE_DIR, "config", "prompts", "revise_plan_prompt.txt"), "r", encoding="utf-8") as f:
    CACHED_REVISE_PLAN_PROMPT = f.read()

# 在导入配置后添加调试日志
logger.debug(f"Server loaded API_KEY: {'*' * len(API_KEY) if API_KEY else 'None'}")
logger.debug(f"Server loaded MODEL_NAME: {MODEL_NAME}")
logger.debug(f"Server loaded API_URL: {API_URL}")

# 包含认证路由
app.include_router(auth_router)

# 添加获取可用模型列表的路由
@app.get("/api/models")
async def get_available_models():
    """获取可用的模型列表
    
    Returns:
        包含模型信息的列表，每个模型包含id和name
    """
    try:
        # 解析AVAILABLE_MODELS环境变量
        models_str = AVAILABLE_MODELS
        if not models_str:
            return {"models": []}
            
        # 解析模型列表
        models = []
        for model_pair in models_str.split(","):
            if ":" in model_pair:
                model_id, model_name = model_pair.strip().split(":")
                models.append({
                    "id": model_id.strip(),
                    "name": model_name.strip()
                })
                
        return {"models": models}
    except Exception as e:
        logger.error(f"获取模型列表时出错: {str(e)}")
        raise HTTPException(status_code=500, detail="获取模型列表失败")

# 重定向根路由到首页
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    # 检查Cookie中是否有token
    user = await auth_service.verify_token(request)
    
    # 如果未登录，显示官网（Landing Page）
    if not user:
        return templates.TemplateResponse("landing.html", {"request": request})
    
    # 确保加载首页
    return templates.TemplateResponse("index.html", {"request": request, "user": user})

# 添加一个独立的 /landing 路由，方便预览
@app.get("/landing", response_class=HTMLResponse)
async def landing_page(request: Request):
    """Landing page - 官网/首页，可用于预览或分享"""
    return templates.TemplateResponse("landing.html", {"request": request})

def extract_between_tags(tag: str, text: str, strip: bool = True) -> List[str]:
    """从文本中提取指定标签之间的内容
    
    支持以下格式:
    1. 完整的XML标签: <tag>content</tag>
    2. 只有开始标签: <tag>content
    3. 标签名可能包含空格
    4. 标签名大小写不敏感
    5. 兼容标签名单复数形式
    
    Args:
        tag: 标签名
        text: 要处理的文本
        strip: 是否去除结果中的首尾空白字符,默认为True
        
    Returns:
        包含标签内容的列表
    """
    try:
        # 确保文本是字符串类型
        if not isinstance(text, str):
            logger.warning(f"Text is not a string: {type(text)}")
            if isinstance(text, bytes):
                text = text.decode('utf-8', errors='replace')
            else:
                text = str(text)
        
        # 检查文本是否是有效的UTF-8字符串
        try:
            text.encode('utf-8').decode('utf-8')
        except UnicodeError:
            # 如果不是有效的UTF-8字符串，尝试修复
            try:
                # 尝试以latin1解码再编码为utf-8
                text = text.encode('latin1').decode('utf-8', errors='replace')
            except Exception as e:
                logger.error(f"尝试修复文本编码失败: {str(e)}")
        
        # 检查文本是否包含Unicode转义序列，如果有则尝试修复
        if '\\u' in text or '\\x' in text:
            text = fix_unicode_escapes(text)
        
        # 处理标签名中可能包含的空格
        tag_pattern = tag.replace(" ", r"\s+")
        
        # 生成单数和复数形式的模式
        # 如果标签已经是复数形式，生成单数形式；如果是单数形式，生成复数形式
        tags_to_try = [tag_pattern]
        
        # 检查标签是否以's'结尾
        if tag_pattern.endswith('s'):
            # 如果是复数形式，添加单数形式
            singular_tag = tag_pattern[:-1]
            tags_to_try.append(singular_tag)
        else:
            # 如果是单数形式，添加复数形式
            plural_tag = tag_pattern + 's'
            tags_to_try.append(plural_tag)
        
        matches = []
        
        # 尝试每个标签形式
        for current_tag in tags_to_try:
            # 尝试匹配完整的XML标签
            complete_pattern = f"<{current_tag}>(.+?)</{current_tag}>"
            current_matches = re.findall(complete_pattern, text, re.DOTALL | re.IGNORECASE)
            
            # 如果没有找到完整标签，取开始标签到文本末尾的全部内容。
            # 注意：不能用 (?=<|$) 非贪婪截断，否则会在 Instructions 内的
            # <tool>、<thinking> 等子标签处提前截断，导致保存内容丢失。
            if not current_matches:
                incomplete_pattern = f"<{current_tag}>([\\s\\S]*)"
                current_matches = re.findall(incomplete_pattern, text, re.IGNORECASE)
            
            if current_matches:
                matches.extend(current_matches)
                logger.debug(f"找到标签 {current_tag} 的匹配: {len(current_matches)}个")
                break  # 找到匹配后可以停止尝试其他形式
        
        if not matches:
            logger.debug(f"未找到标签 {tag} 或其单复数形式的匹配")
            return []
            
        logger.debug(f"提取标签 {tag}（含单复数形式），找到 {len(matches)} 个匹配")
        if matches:
            logger.debug(f"第一个匹配内容长度: {len(matches[0])}")
            
        # 移除重复的匹配结果
        unique_matches = list(dict.fromkeys(matches))
        
        # 处理每个匹配结果，确保它们是有效的UTF-8字符串
        processed_matches = []
        for m in unique_matches:
            if m:
                # 确保匹配结果是有效的UTF-8字符串
                try:
                    if isinstance(m, bytes):
                        m = m.decode('utf-8', errors='replace')
                    # 检查并修复可能的Unicode转义序列
                    if '\\u' in m or '\\x' in m:
                        m = fix_unicode_escapes(m)
        # 根据strip参数决定是否去除空白字符
                    processed_matches.append(m.strip() if strip else m)
                except Exception as e:
                    logger.error(f"处理匹配结果时出错: {str(e)}")
                    processed_matches.append(m if isinstance(m, str) else str(m))
        
        return processed_matches
            
    except Exception as e:
        logger.error(f"Error extracting tags: {str(e)}")
        return []

def extract_variables(text: str) -> Set[str]:
    """提取文本中的所有变量名
    
    支持三种格式:
    1. {$VARIABLE} - 标准格式
    2. {{VARIABLE}} - 双大括号格式
    3. ${VARIABLE} - 美元符号格式
    
    Args:
        text: 要处理的文本
        
    Returns:
        变量名集合
    """
    # 匹配三种格式的变量
    standard_vars = set(re.findall(r'\{\$([A-Za-z0-9_]+)\}', text))
    double_brace_vars = set(re.findall(r'\{\{([A-Za-z0-9_]+)\}\}', text))
    dollar_vars = set(re.findall(r'\$\{([A-Za-z0-9_]+)\}', text))
    
    # 合并所有格式的结果
    return standard_vars.union(double_brace_vars).union(dollar_vars)

def find_free_floating_variables(prompt: str) -> List[str]:
    """检测提示词中的浮动变量
    
    Args:
        prompt: 提示词文本
        
    Returns:
        浮动变量列表（在XML标签外的变量）
    """
    variable_usages = re.findall(r'\{\$[A-Z0-9_]+\}', prompt)
    free_floating_variables = []
    
    for variable in variable_usages:
        preceding_text = prompt[:prompt.index(variable)]
        open_tags = set()
        
        i = 0
        while i < len(preceding_text):
            if preceding_text[i] == '<':
                if i + 1 < len(preceding_text) and preceding_text[i + 1] == '/':
                    closing_tag = preceding_text[i + 2:].split('>', 1)[0]
                    open_tags.discard(closing_tag)
                    i += len(closing_tag) + 3
                else:
                    opening_tag = preceding_text[i + 1:].split('>', 1)[0]
                    open_tags.add(opening_tag)
                    i += len(opening_tag) + 2
            else:
                i += 1
                
        if not open_tags:
            free_floating_variables.append(variable)
            
    return free_floating_variables

async def remove_inapt_floating_variables(prompt: str) -> str:
    """处理提示词中的不当浮动变量
    
    Args:
        prompt: 原始提示词
        
    Returns:
        处理后的提示词
    """
    try:
        # 读取提示词模板
        with open(os.path.join(BASE_DIR, "config", "prompts", "remove_floating_variables.txt"), "r", encoding="utf-8") as f:
            remove_floating_variables_prompt = f.read()
        
        # 调用API获取重写后的提示词
        message = await create_chat_completion(
            messages=[{
                "role": "user",
                "content": remove_floating_variables_prompt.replace("{$PROMPT}", prompt)
            }]
        )
        
        # 提取重写后的提示词
        rewritten_prompts = extract_between_tags("rewritten_prompt", message)
        if not rewritten_prompts:
            logger.error("No rewritten prompt found in API response")
            return prompt
            
        return rewritten_prompts[0].strip()
        
    except Exception as e:
        logger.error(f"Error removing floating variables: {str(e)}")
        return prompt

class Task(BaseModel):
    project_id: str
    task: str
    variables: List[str] = []
    stream: bool = False
    # 是否保存生成结果为历史版本；为确保不自动保存，默认 False
    save: bool = False

class ImproveRequest(BaseModel):
    project_id: str
    prompt_id: str
    metaprompt: str
    improve_instructions: str

class ContentPart(BaseModel):
    """消息内容的一部分（文本或图片）"""
    type: str  # "text" 或 "image_url"
    text: Optional[str] = None  # 当 type="text" 时使用
    image_url: Optional[dict] = None  # 当 type="image_url" 时使用，格式：{"url": "data:image/..."}

class UserMessageItem(BaseModel):
    """单条 user 消息，支持两种格式"""
    # 新格式：直接使用 content 数组（前端已组装好的多模态内容）
    content: Optional[List[ContentPart]] = None
    # 旧格式：分开的 text 和 images（兼容旧版）
    text: Optional[str] = ""
    images: Optional[List[str]] = None  # base64 编码的图片列表

class TestRequest(BaseModel):
    # 兼容旧字段：prompt 表示单条 user 内容
    prompt: Optional[str] = None
    # 新字段：明确的 system 与 user 角色内容
    system_prompt: Optional[str] = ""
    user_prompt: Optional[str] = None
    # 图片列表：支持多模态输入，每项为 base64 编码的图片数据 (data:image/xxx;base64,...)（兼容旧版）
    images: Optional[List[str]] = None
    # 新版：支持多条 user message，每条可包含文本和图片
    user_messages: Optional[List[UserMessageItem]] = None
    model: str
    max_tokens: int = 4096
    project_id: str  # 添加项目ID字段

def build_user_message(text_content: str, images: Optional[List[str]] = None) -> dict:
    """构建单条 user 消息，支持多模态（文本+图片）
    
    Args:
        text_content: 文本内容
        images: 图片列表，每项为 base64 编码的图片数据 (data:image/xxx;base64,...)
    
    Returns:
        符合 OpenAI API 格式的 user 消息
    """
    # 如果没有图片，返回简单的文本消息
    if not images or len(images) == 0:
        return {"role": "user", "content": text_content}
    
    # 有图片时，使用多模态格式
    content_parts = []
    
    # 先添加文本部分（如果有）
    if text_content:
        content_parts.append({"type": "text", "text": text_content})
    
    # 添加图片部分
    for image_data in images:
        content_parts.append({
            "type": "image_url",
            "image_url": {"url": image_data}
        })
    
    return {"role": "user", "content": content_parts}

def build_user_messages(request: 'TestRequest') -> List[dict]:
    """根据请求构建 user 消息列表
    
    支持多种格式：
    1. 新格式：user_messages[].content（前端已组装好的多模态内容数组）
    2. 旧格式：user_messages[].text + images（分开的文本和图片）
    3. 兼容格式：user_prompt + images（单条消息）
    
    Args:
        request: TestRequest 请求对象
    
    Returns:
        user 消息列表
    """
    messages = []
    
    # 优先使用 user_messages
    if request.user_messages and len(request.user_messages) > 0:
        logger.info(f"[DEBUG build_user_messages] 使用 user_messages 格式，共 {len(request.user_messages)} 条")
        for idx, msg in enumerate(request.user_messages):
            # 新格式：直接使用 content 数组
            if msg.content and len(msg.content) > 0:
                logger.info(f"[DEBUG build_user_messages] msg[{idx}] 使用新格式 content，共 {len(msg.content)} 个 parts")
                # 将 ContentPart 转换为 dict 格式
                content_parts = []
                for part in msg.content:
                    if part.type == "text" and part.text:
                        content_parts.append({"type": "text", "text": part.text})
                        logger.info(f"[DEBUG build_user_messages] 添加 text part: {part.text[:50]}...")
                    elif part.type == "image_url" and part.image_url:
                        content_parts.append({"type": "image_url", "image_url": part.image_url})
                        logger.info(f"[DEBUG build_user_messages] 添加 image_url part")
                
                if content_parts:
                    messages.append({"role": "user", "content": content_parts})
                    logger.info(f"[DEBUG build_user_messages] 构建了包含 {len(content_parts)} 个 parts 的 user 消息")
            # 旧格式：使用 text + images
            elif msg.text or (msg.images and len(msg.images) > 0):
                logger.info(f"[DEBUG build_user_messages] msg[{idx}] 使用旧格式 text+images")
                user_msg = build_user_message(msg.text or "", msg.images)
                messages.append(user_msg)
    else:
        # 回退到兼容格式：user_prompt + images
        logger.info(f"[DEBUG build_user_messages] 回退到兼容格式 user_prompt+images")
        usr_content = request.user_prompt if request.user_prompt is not None else request.prompt
        user_msg = build_user_message(usr_content or "", request.images)
        messages.append(user_msg)
    
    logger.info(f"[DEBUG build_user_messages] 最终构建了 {len(messages)} 条 user 消息")
    return messages

class ProjectCreate(BaseModel):
    name: str = Field(..., max_length=50)  # 限制项目名称最大长度为50

class ProjectRename(BaseModel):
    name: str = Field(..., max_length=50)  # 限制项目名称最大长度为50

class ReviseRequest(BaseModel):
    project_id: str
    improve_instructions: str
    planning: str
    prompt: str

class SavePromptRequest(BaseModel):
    """保存提示词请求模型（兼容旧格式）"""
    project_id: str
    system_prompt: Optional[str] = None
    user_prompt: Optional[str] = ""  # User Prompt 可选，默认为空
    variables: List[str] = Field(default_factory=list)  # 简化为字符串列表，与生成时的格式保持一致
    # 兼容旧字段
    content: Optional[str] = None
    name: Optional[str] = None  # 目前未使用，仅保留以兼容前端传值

    @validator("system_prompt", pre=True, always=True)
    def ensure_system_prompt(cls, value, values):
        # 兼容旧字段 content
        if value is None or (isinstance(value, str) and not value.strip()):
            content = values.get("content")
            if content and content.strip():
                return content
            raise ValueError("system_prompt 不能为空")
        return value

    @validator("user_prompt", pre=True, always=True)
    def default_user_prompt(cls, value):
        return value or ""

    @validator("variables", pre=True, always=True)
    def normalize_variables(cls, value):
        if value is None:
            return []
        if isinstance(value, dict):
            # 旧实现会传 {variable: default_value}
            return list(value.keys())
        if isinstance(value, list):
            return value
        # 兜底：将单一值转成列表
        return [str(value)]

class VersionListRequest(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)
    sort_by: str = Field(default="version", pattern="^(version|created_at)$")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")

async def create_chat_completion(model=None, messages=None, max_tokens=4096, temperature=0, max_retries=3):
    """调用API生成对话内容
    
    Args:
        model: 使用的模型名称
        messages: 对话消息列表
        max_tokens: 最大生成长度
        temperature: 温度参数
        max_retries: 最大重试次数
        
    Returns:
        生成的内容或完整响应JSON对象
    """
    last_error = None
    # 添加重试机制
    for retry_count in range(max_retries):
        try:
            # 确保model参数正确
            if model is None:
                model = MODEL_NAME
            
            # 检查模型是否支持多模态，不支持则转换为纯文本
            if not is_vision_model(model):
                messages = convert_messages_for_text_only_model(messages)
                logger.info(f"[DEBUG] 模型 {model} 不支持多模态，已将消息转换为纯文本格式")
            
            # 计算请求大小
            payload_size = len(str(messages))
            if payload_size > 150000:  # 调整为更合理的限制，大约对应50000 tokens
                logger.warning(f"Request payload size ({payload_size} chars) exceeds recommended limit. Truncating...")
                # 截断最后一条消息
                last_message = messages[-1]["content"]
                max_last_message_size = 150000 - len(str(messages[:-1])) - 100  # 留些余量
                messages[-1]["content"] = last_message[:max_last_message_size]
                logger.debug(f"Truncated last message to {len(messages[-1]['content'])} chars")
            
            # 增加超时时间，但不要超过Vercel函数限制
            timeout = ClientTimeout(total=100)  # 设置为100秒，避免超过Vercel限制
            logger.debug(f"开始API请求 (尝试 {retry_count+1}/{max_retries})...")
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                payload = {
                    "model": model,
                    "messages": messages,
                    "max_tokens": max_tokens
                }
                
                headers = {
                    'Accept': 'application/json',
                    'Authorization': f'Bearer {API_KEY}',
                    'Content-Type': 'application/json'
                }
                
                logger.debug(f"Sending request to API with payload length: {len(str(payload))}")
                logger.debug(f"API URL: {API_URL}")
                
                async with session.post(API_URL, json=payload, headers=headers) as response:
                    logger.debug(f"Received response with status: {response.status}")
                    
                    # 直接获取二进制响应，以便更好地控制解码
                    response_bytes = await response.read()
                    response_text = response_bytes.decode('utf-8', errors='replace')
                    
                    # 记录响应信息
                    logger.debug(f"Response data length: {len(response_text)}")
                    if len(response_text) > 500:
                        logger.debug(f"Raw response data (first 500 chars): {response_text[:500]}...")
                    else:
                        logger.debug(f"Raw response data: {response_text}")
                    
                    if response.status != 200:
                        error_detail = f"API请求失败: HTTP {response.status}"
                        try:
                            error_json = json.loads(response_text)
                            if isinstance(error_json, dict) and "error" in error_json:
                                error_detail += f" - {error_json['error']}"
                        except:
                            error_detail += f" - {response_text[:200]}"
                        
                        logger.error(error_detail)
                        last_error = HTTPException(status_code=response.status, detail=error_detail)
                        # 如果状态码表示服务器错误(>=500)，重试
                        if response.status >= 500 and retry_count < max_retries - 1:
                            logger.warning(f"服务器错误({response.status})，将在2秒后重试...")
                            await asyncio.sleep(2)  # 添加延迟防止立即重试
                            continue
                        raise last_error
                    
                    # 修复Unicode转义序列和编码问题
                    fixed_response_text = fix_unicode_escapes(response_text)
                    if fixed_response_text != response_text:
                        logger.debug("成功修复了响应文本中的编码问题")
                        response_text = fixed_response_text
                    
                    try:
                        # 尝试解析为JSON对象
                        result = json.loads(response_text)
                        logger.debug(f"API response structure keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
                        
                        # 检测特殊格式：混元API (Response字段)
                        if isinstance(result, dict) and "Response" in result:
                            logger.info(f"API响应类型: <class 'dict'> (混元API格式)")
                            # 直接返回完整JSON对象
                            return result
                        
                        # 从JSON中提取文本
                        extracted_text = extract_text_from_json(result)
                        if extracted_text:
                            logger.debug(f"成功从JSON中提取文本(长度: {len(extracted_text)})")
                            # 返回提取的文本内容
                            return extracted_text
                        
                        # 如果无法提取文本，返回原始JSON对象
                        logger.warning("无法从JSON中提取文本，返回原始JSON对象")
                        return result
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON解析失败: {str(e)}")
                        # 如果不是JSON，直接返回文本
                        return response_text
                        
        except asyncio.TimeoutError:
            last_error = HTTPException(status_code=504, detail="请求超时")
            logger.error(f"请求超时 (尝试 {retry_count+1}/{max_retries})")
            if retry_count < max_retries - 1:
                logger.warning(f"将在3秒后重试...")
                await asyncio.sleep(3)  # 添加更长的延迟
                continue
            
        except aiohttp.ClientError as e:
            last_error = HTTPException(status_code=500, detail=f"请求失败: {str(e)}")
            logger.error(f"请求失败: {str(e)} (尝试 {retry_count+1}/{max_retries})")
            if retry_count < max_retries - 1:
                logger.warning(f"将在2秒后重试...")
                await asyncio.sleep(2)
                continue
            
        except Exception as e:
            last_error = HTTPException(status_code=500, detail=f"API调用失败: {str(e)}")
            logger.error(f"API调用失败: {str(e)} (尝试 {retry_count+1}/{max_retries})")
            if retry_count < max_retries - 1:
                logger.warning(f"将在2秒后重试...")
                await asyncio.sleep(2)
                continue
            
    # 如果所有重试都失败，抛出最后一个错误
    if last_error:
        raise last_error
    else:
        raise HTTPException(status_code=500, detail="API请求失败，所有重试均失败")

def extract_text_from_json(json_obj):
    """从JSON对象中递归提取文本内容"""
    try:
        # 处理字符串
        if isinstance(json_obj, str):
            return fix_unicode_escapes(json_obj)
        
        # 处理字典
        if isinstance(json_obj, dict):
            # 处理混元API格式 (Response+Choices格式)
            if "Response" in json_obj:
                logger.debug("处理混元模型Response格式")
                
                # 记录整个响应结构
                logger.debug(f"混元响应结构: {json.dumps({k: '...' for k in json_obj['Response'].keys()}, ensure_ascii=False)}")
                
                # 从Response字段获取数据
                resp_data = json_obj.get("Response", {})
                
                # 提取混元API内容
                if "Choices" in resp_data and isinstance(resp_data["Choices"], list) and resp_data["Choices"]:
                    logger.debug("从混元响应Choices中提取内容")
                    choice = resp_data["Choices"][0]
                    if "Message" in choice and "Content" in choice["Message"]:
                        content = choice["Message"]["Content"]
                        logger.debug(f"从混元API Choices提取内容: {content[:100]}...")
                        return fix_unicode_escapes(content.strip())
                
                # 检查ResponseText字段
                if "ResponseText" in resp_data:
                    content = resp_data["ResponseText"]
                    logger.debug(f"从混元API ResponseText提取内容: {content[:100]}...")
                    return fix_unicode_escapes(content.strip())
                
                # 如果都没有，返回完整Response结构
                logger.debug("未能从混元API特定字段提取内容，返回完整响应")
                return json.dumps(resp_data, ensure_ascii=False)
            
            # 处理302ai API特定的响应格式（如content列表）
            if "content" in json_obj and isinstance(json_obj["content"], list):
                # 添加调试日志
                logger.debug(f"发现302ai格式响应: {json.dumps(json_obj, ensure_ascii=False)}")
                
                # 合并所有text内容
                full_text = ""
                for item in json_obj["content"]:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text = item.get("text", "")
                        # 记录每个文本片段
                        logger.debug(f"处理文本片段: {text[:100]}...")
                        # 确保文本是UTF-8编码，如果是bytes则解码
                        if isinstance(text, bytes):
                            text = text.decode('utf-8', errors='replace')
                        full_text += text
                
                # 如果有内容，尝试提取标签内的内容或返回整个文本
                if full_text:
                    logger.debug(f"从content列表提取的文本长度: {len(full_text)}")
                    # 提取product_description标签内容
                    try:
                        matches = re.findall(r'<product_description>(.*?)</product_description>', full_text, re.DOTALL | re.IGNORECASE)
                        if matches:
                            return matches[0].strip()
                    except Exception as e:
                        logger.error(f"提取标签内容失败: {str(e)}")
                    return full_text.strip()
            
            # 处理message格式
            if "message" in json_obj:
                message = json_obj["message"]
                if isinstance(message, dict) and "content" in message:
                    content = message["content"]
                    if isinstance(content, str):
                        return fix_unicode_escapes(content)
                    elif isinstance(content, list):
                        # 处理OpenAI的内容列表格式
                        text_parts = []
                        for item in content:
                            if isinstance(item, dict) and item.get("type") == "text":
                                text = item.get("text", "")
                                if text:
                                    text_parts.append(fix_unicode_escapes(text))
                        content = "".join(text_parts)
                    return fix_unicode_escapes(content.strip())
            
            # 处理choices格式
            if "choices" in json_obj and json_obj["choices"]:
                logger.debug("从choices字段提取内容")
                choice = json_obj["choices"][0]
                if isinstance(choice, dict):
                    if "message" in choice and isinstance(choice["message"], dict):
                        content = choice["message"].get("content", "")
                        if isinstance(content, bytes):
                            content = content.decode('utf-8', errors='replace')
                        elif isinstance(content, list) and all(isinstance(item, dict) for item in content):
                            # 处理OpenAI格式的内容列表
                            text_parts = []
                            for item in content:
                                if item.get("type") == "text":
                                    text = item.get("text", "")
                                    if isinstance(text, bytes):
                                        text = text.decode('utf-8', errors='replace')
                                    text_parts.append(text)
                            content = "".join(text_parts)
                        return fix_unicode_escapes(content.strip())
                    if "content" in choice:
                        content = choice["content"]
                        if isinstance(content, bytes):
                            content = content.decode('utf-8', errors='replace')
                        return fix_unicode_escapes(content.strip())
                    if "text" in choice:
                        text = choice["text"]
                        if isinstance(text, bytes):
                            text = text.decode('utf-8', errors='replace')
                        return fix_unicode_escapes(text.strip())
            
            # 尝试从text字段提取
            if "text" in json_obj:
                text = json_obj["text"]
                if isinstance(text, str):
                    return fix_unicode_escapes(text)
            
            # 如果都没有找到，递归处理所有值
            for key, value in json_obj.items():
                result = extract_text_from_json(value)
                if result:
                    return result
        
        # 处理列表
        if isinstance(json_obj, list):
            for item in json_obj:
                result = extract_text_from_json(item)
                if result:
                    return result
        
        return None
    except Exception as e:
        logger.error(f"从JSON中提取文本失败: {str(e)}")
        return None

# 项目相关接口
@app.post("/api/projects")
async def create_project(
    project: dict, 
    request: Request,
    current_user = Depends(get_current_user)
):
    logger.info(f"创建项目: {project['name']}")
    
    # 检查用户认证状态
    auth_error = require_auth(current_user)
    if auth_error:
        return auth_error
    
    logger.debug(f"当前用户详情: ID={current_user.id}, email={current_user.email}")
    
    try:       
        # 检查用户ID是否有效
        if not current_user.id:
            logger.error(f"无效的用户ID: {current_user.id}")
            return error_response(400, "无效的用户ID", "invalid_user_id")
            
        project_data = {
            "name": project["name"],
            "description": project.get("description", ""),
            "user_id": current_user.id
        }
        
        project_result = await supabase_db.create_project(**project_data)
        
        logger.debug(f"Supabase创建项目结果: {project_result}")
        
        if not project_result:
            logger.error(f"项目创建失败，user_id={current_user.id}")
            # 获取最后一个错误信息
            last_error = getattr(supabase_db, "last_error", "未知错误")
            return error_response(500, f"项目创建失败: {last_error}", "project_creation_failed")
        
        # 返回创建的项目信息
        return success_response(project_result, "项目创建成功")
    except Exception as e:
        # 记录详细的错误信息
        import traceback
        error_traceback = traceback.format_exc()
        logger.error(f"创建项目过程中发生异常: {str(e)}")
        logger.error(f"异常堆栈跟踪: {error_traceback}")
        return error_response(500, f"创建项目失败: {str(e)}", "project_creation_exception")

@app.get("/api/projects")
async def get_projects(current_user = Depends(get_current_user)):
    logger.info(f"获取项目列表: 用户ID: {current_user.id}")
    try:
        # 获取用户拥有的项目
        projects = await supabase_db.get_projects(user_id=current_user.id)
        logger.debug(f"找到 {len(projects)} 个项目")
        return success_response(projects, "获取项目列表成功")
    except Exception as e:
        logger.error(f"获取项目列表失败: {str(e)}")
        return error_response(500, f"获取项目列表失败: {str(e)}", "get_projects_failed")

@app.get("/api/projects/latest")
async def get_latest_project_and_prompt(current_user = Depends(get_current_user)):
    """返回当前用户"最新项目 + 该项目最新一版提示词"的轻量数据，用于首屏秒开。
    返回结构：{ project: {id,name,updated_at}, prompt: {id,content,version,variables,created_at} }
    """
    try:
        projects = await supabase_db.get_projects(user_id=current_user.id) or []
        if not projects:
            return JSONResponse(status_code=200, content={"success": True, "data": None})
        # 选最近更新项目（若没有 updated_at 字段，则取列表首项）
        try:
            latest_project = max(projects, key=lambda p: p.get("updated_at", ""))
        except Exception:
            latest_project = projects[0]

        # 找到该项目最新一版
        history = await supabase_db.get_prompt_history(latest_project["id"]) or []
        latest_prompt = None
        if history:
            try:
                latest_prompt = max(history, key=lambda x: (x.get("version", 0), x.get("created_at", "")))
            except Exception:
                latest_prompt = history[0]

        data = {
            "project": {
                "id": latest_project["id"],
                "name": latest_project.get("name", ""),
                "updated_at": latest_project.get("updated_at")
            },
            "prompt": None
        }
        if latest_prompt:
            data["prompt"] = {
                "id": latest_prompt.get("id"),
                "content": latest_prompt.get("system_prompt") or latest_prompt.get("content", ""),
                "version": latest_prompt.get("version", 0),
                "variables": latest_prompt.get("variables", {}).get("variables", []) if isinstance(latest_prompt.get("variables"), dict) else [],
                "created_at": latest_prompt.get("created_at")
            }
        return JSONResponse(status_code=200, content={"success": True, "data": data})
    except Exception as e:
        logger.error(f"获取最新项目与提示词失败: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})

@app.get("/api/projects/{project_id}/prompts")
async def get_project_prompts(
    project_id: str,
    current_user: UserInfo = Depends(get_current_user)
):
    """获取项目的所有提示词版本"""
    try:
        logger.info(f"开始获取项目[{project_id}]的提示词历史")
        
        # 使用 Supabase 获取提示词历史记录
        try:
            prompt_history = await supabase_db.get_prompt_history(project_id)
            logger.info(f"成功获取提示词历史，条目数: {len(prompt_history) if prompt_history else 0}")
        except Exception as inner_e:
            logger.error(f"获取提示词历史时发生错误: {str(inner_e)}", exc_info=True)
            raise Exception(f"获取提示词历史失败: {str(inner_e)}")
        
        if not prompt_history:
            logger.info(f"项目[{project_id}]没有提示词历史")
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "data": []
                }
            )
        
        # 格式化返回数据
        prompts_data = []
        for ph in prompt_history:
            try:
                # 处理variables字段，它可能是字符串或字典
                variables_list = []
                if ph["variables"]:
                    # 如果是字符串，尝试解析为JSON
                    if isinstance(ph["variables"], str):
                        try:
                            variables_obj = json.loads(ph["variables"])
                            # 提取变量列表
                            if isinstance(variables_obj, dict) and "variables" in variables_obj:
                                variables_list = variables_obj["variables"]
                            elif isinstance(variables_obj, list):
                                variables_list = variables_obj
                            else:
                                variables_list = []
                        except json.JSONDecodeError:
                            logger.warning(f"无法解析变量JSON: {ph['variables']}")
                            variables_list = []
                    # 如果是字典，直接提取
                    elif isinstance(ph["variables"], dict):
                        variables_list = ph["variables"].get("variables", [])
                
                prompt_data = {
                    "id": ph["id"],
                    # 向后兼容：同时返回 content 和 system_prompt
                    "content": ph.get("system_prompt") or ph.get("content", ""),
                    "system_prompt": ph.get("system_prompt") or ph.get("content", ""),
                    "user_prompt": ph.get("user_prompt", ""),
                    "version": ph["version"],
                    "variables": variables_list,
                    "created_at": ph["created_at"],
                    "change_summary": ph.get("change_summary", "")
                }
                prompts_data.append(prompt_data)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"成功处理提示词: ID={ph['id']}, 变量数={len(variables_list)}")
            except KeyError as e:
                logger.error(f"历史记录数据格式错误: {str(e)}, 记录: {ph}")
                continue
        
        logger.info(f"成功处理提示词数据，返回{len(prompts_data)}条记录")
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": prompts_data
            }
        )
        
    except Exception as e:
        logger.error(f"获取项目提示词失败: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"获取提示词列表失败: {str(e)}"
            }
        )

@app.get("/api/projects/{project_id}/prompts/latest")
async def get_latest_prompt(
    project_id: str,
    current_user: UserInfo = Depends(get_current_user)
):
    """获取项目最新一版提示词（轻量）。
    返回字段：id, content, version, variables(列表), created_at
    """
    try:
        # 权限校验
        project = await supabase_db.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="项目不存在")
        if project["user_id"] != current_user.id:
            raise HTTPException(status_code=403, detail="没有权限访问此项目")

        latest = None
        # 如果有专用方法，优先使用
        get_latest = getattr(supabase_db, "get_latest_prompt_history", None)
        if callable(get_latest):
            try:
                latest = get_latest(project_id)
            except Exception as e:
                logger.warning(f"调用get_latest_prompt_history失败: {str(e)}，回退到列表选择")

        if not latest:
            # 回退：从历史列表选最大version或最近创建
            history = await supabase_db.get_prompt_history(project_id) or []
            if not history:
                return JSONResponse(status_code=200, content={"success": True, "data": None})
            # 优先按version排序
            try:
                latest = max(history, key=lambda x: (x.get("version", 0), x.get("created_at", "")))
            except Exception:
                latest = history[0]

        data = {
            "id": latest["id"],
            # 向后兼容：同时返回 content 和 system_prompt
            "content": latest.get("system_prompt") or latest.get("content", ""),
            "system_prompt": latest.get("system_prompt") or latest.get("content", ""),
            "user_prompt": latest.get("user_prompt", ""),
            "version": latest.get("version", 0),
            "variables": latest["variables"].get("variables", []) if latest.get("variables") else [],
            "created_at": latest.get("created_at")
        }
        return JSONResponse(status_code=200, content={"success": True, "data": data})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取最新提示词失败: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})

@app.put("/api/projects/{project_id}/rename")
async def rename_project_api(
    project_id: str, 
    project: ProjectRename,
    current_user = Depends(get_current_user)
):
    logger.info(f"重命名项目: 项目ID: {project_id}, 新名称: {project.name}, 用户ID: {current_user.id}")
    
    try:
        # 先检查项目是否存在，无论它属于谁
        existing_project = await supabase_db.get_project(project_id)
        if not existing_project:
            logger.warning(f"项目不存在: {project_id}")
            return error_response(404, "项目不存在", "project_not_found")
            
        # 检查项目是否属于当前用户
        if existing_project.get("user_id") != current_user.id:
            logger.warning(f"用户 {current_user.id} 尝试重命名不属于他的项目 {project_id}")
            return error_response(403, "您没有权限修改此项目", "insufficient_permissions")
        
        # 使用增强的重命名函数
        updated_project = await rename_project(project_id, project.name, supabase_db)
        if not updated_project:
            return error_response(500, "项目重命名失败", "project_rename_failed")
            
        return success_response(updated_project, "项目重命名成功")
    except Exception as e:
        logger.error(f"项目重命名失败: {str(e)}")
        return error_response(500, f"项目重命名失败: {str(e)}", "project_rename_exception")

@app.delete("/api/projects/{project_id}")
async def delete_project(
    project_id: str,
    current_user = Depends(get_current_user)
):
    logger.info(f"删除项目: 项目ID: {project_id}, 用户ID: {current_user.id}")
    
    try:
        # 先检查项目是否存在，无论它属于谁
        existing_project = await supabase_db.get_project(project_id)
        if not existing_project:
            logger.warning(f"项目不存在: {project_id}")
            return error_response(404, "项目不存在", "project_not_found")
            
        # 检查项目是否属于当前用户
        if existing_project.get("user_id") != current_user.id:
            logger.warning(f"用户 {current_user.id} 尝试删除不属于他的项目 {project_id}")
            return error_response(403, "您没有权限删除此项目", "insufficient_permissions")
        
        # 使用增强的删除函数，确保删除所有相关数据
        success = await delete_project_with_history(project_id, supabase_db)
        if not success:
            return error_response(500, "项目删除失败", "project_deletion_failed")
            
        return success_response({"status": "success", "message": "项目已成功删除"}, "项目删除成功")
    except Exception as e:
        logger.error(f"项目删除失败: {str(e)}")
        return error_response(500, f"项目删除失败: {str(e)}", "project_deletion_exception")

# 路由处理函数
def _generate_sse_generator(task: Task, current_user):
    """构造生成提示词的SSE生成器（共享给 /generate 和 /generate/stream）。"""
    # 构造消息
    prompt_text = CACHED_METAPROMPT.replace("{{TASK}}", task.task)

    async def sse_generator():
        accumulated = ""
        visible_instructions_so_far = ""  # 已经输出给前端的 <Instructions> 内文本
        logger.info("开始流式生成...")

        # 通过队列解耦上游读取，支持心跳保活
        queue: asyncio.Queue = asyncio.Queue()
        upstream_done = asyncio.Event()
        heartbeat_interval_seconds = 12.0

        async def _read_upstream_to_queue():
            try:
                async for delta in create_chat_completion_stream(
                    messages=[{"role": "user", "content": prompt_text}],
                    max_tokens=4096
                ):
                    await queue.put(delta)
            except Exception as e:
                logger.error(f"上游读取失败: {str(e)}")
            finally:
                upstream_done.set()

        reader_task = asyncio.create_task(_read_upstream_to_queue())

        # 消费队列，定时发送心跳，避免浏览器卡顿认为连接空闲
        while True:
            try:
                delta = await asyncio.wait_for(queue.get(), timeout=heartbeat_interval_seconds)
            except asyncio.TimeoutError:
                # 心跳：发送一个空增量，触发浏览器刷新但不改变显示
                yield "data: {\"delta\": \"\"}\n\n"
                if upstream_done.is_set() and queue.empty():
                    break
                continue

            if delta:
                accumulated += delta
                # 直接推送上游增量，由前端进行 <Instructions> 过滤，避免 O(n^2) 重复扫描导致卡顿
                yield f"data: {json.dumps({'delta': delta})}\n\n"

            if upstream_done.is_set() and queue.empty():
                break

        # 2) 提取模板并保存
        try:
            logger.info(f"流式完成，开始提取内容。原始内容长度: {len(accumulated)}")
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"原始内容前200字符: {accumulated[:200]}...")
            template = extract_prompt(accumulated) or accumulated
            logger.info(f"提取后内容长度: {len(template)}")
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"提取后内容前200字符: {template[:200]}...")
            variables = list(extract_variables(template))

            # 预览模式：不自动保存历史记录，交由前端在“应用到 System Prompt”时调用保存接口
            result_obj = {
                "prompt": template,
                "variables": variables,
                "version": 0,
                "id": ""
            }
            logger.info("生成完成(预览模式)，未保存历史记录")
        except Exception as e:
            logger.error(f"post-process failed: {str(e)}")
            result_obj = {"prompt": template if 'template' in locals() else accumulated, "variables": [], "version": 0, "id": ""}

        # 3) 结束事件
        yield "event: done\n" + f"data: {json.dumps(result_obj)}\n\n"

    return sse_generator

@app.post("/generate")
async def generate_prompt(
    task: Task,
    current_user = Depends(get_current_user)
):
    """生成提示词：默认以SSE流式返回。非流式实现保留为注释，作为参考。"""
    try:
        logger.info(f"收到生成请求: project_id={task.project_id}, stream={task.stream}")
        # 检查项目是否存在
        project = await supabase_db.get_project(task.project_id)
        if not project:
            raise HTTPException(status_code=404, detail="项目不存在")
        # 检查项目权限
        if project["user_id"] != current_user.id:
            raise HTTPException(status_code=403, detail="没有权限访问此项目")

        # 默认流式
        logger.info("使用流式模式生成提示词（默认）")
        headers = {
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
        return StreamingResponse(
            _generate_sse_generator(task, current_user)(),
            media_type="text/event-stream",
            headers=headers
        )

        # 以下为旧的非流式实现，已不再使用，仅供参考
        # template = await generate_prompt_template(task.task)
        # variables = list(extract_variables(template))
        # latest_version = supabase_db.get_latest_prompt_version(task.project_id) or 0
        # history_data = {
        #     "project_id": task.project_id,
        #     "content": template,
        #     "version": latest_version + 1,
        #     "user_id": current_user.id,
        #     "change_summary": "Generated new prompt",
        #     "variables": {"variables": variables}
        # }
        # prompt_history = supabase_db.create_prompt_history(**history_data)
        # if not prompt_history:
        #     raise HTTPException(status_code=500, detail="Failed to save prompt history")
        # return {"prompt": template, "variables": variables, "version": prompt_history["version"], "id": prompt_history["id"]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Generate prompt failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def is_vision_model(model_name: str) -> bool:
    """检查模型是否支持视觉/图片输入"""
    if not model_name:
        return False
    model_lower = model_name.lower()
    # 支持视觉的模型关键词
    vision_keywords = ['vision', 'gpt-4o', 'gpt-4-turbo', 'gemini', 'claude-3', 'qwen-vl', 'glm-4v']
    return any(kw in model_lower for kw in vision_keywords)

def convert_messages_for_text_only_model(messages: List[dict]) -> List[dict]:
    """将多模态消息转换为纯文本格式（用于不支持图片的模型）
    
    Args:
        messages: 可能包含多模态内容的消息列表
        
    Returns:
        转换后的纯文本消息列表
    """
    converted = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        
        # 如果 content 是字符串，直接使用
        if isinstance(content, str):
            converted.append({"role": role, "content": content})
        # 如果 content 是数组（多模态格式），提取文本部分
        elif isinstance(content, list):
            text_parts = []
            image_count = 0
            for part in content:
                if isinstance(part, dict):
                    if part.get("type") == "text":
                        text_parts.append(part.get("text", ""))
                    elif part.get("type") == "image_url":
                        image_count += 1
                elif isinstance(part, str):
                    text_parts.append(part)
            
            combined_text = "\n".join(text_parts)
            if image_count > 0:
                combined_text += f"\n\n[注意：原消息包含 {image_count} 张图片，但当前模型不支持图片输入，图片已被忽略]"
            converted.append({"role": role, "content": combined_text})
        else:
            converted.append({"role": role, "content": str(content)})
    
    return converted

async def create_chat_completion_stream(model=None, messages=None, max_tokens=4096, temperature=0):
    """以流式方式调用上游接口，逐步产出文本增量。
    
    优先使用与 OpenAI 兼容的 stream 数据格式；若上游不支持流式，
    则退化为一次性返回完整文本并以单块输出。
    """
    try:
        if model is None:
            model = MODEL_NAME
        
        # 检查模型是否支持多模态，不支持则转换为纯文本
        if not is_vision_model(model):
            messages = convert_messages_for_text_only_model(messages)
            logger.info(f"[DEBUG] 模型 {model} 不支持多模态，已将消息转换为纯文本格式")
        
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "stream": True
        }
        headers = {
            'Accept': 'text/event-stream',
            'Authorization': f'Bearer {API_KEY}',
            'Content-Type': 'application/json'
        }
        timeout = ClientTimeout(total=100)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(API_URL, json=payload, headers=headers) as response:
                # 如果不是200，尝试读取完整文本作为降级
                if response.status != 200:
                    text = await response.text()
                    yield text
                    return
                # 逐行读取SSE
                async for raw_line in response.content:
                    try:
                        line = raw_line.decode('utf-8', errors='replace').strip()
                    except Exception:
                        continue
                    if not line:
                        continue
                    # 兼容 OpenAI SSE: data: {json}
                    if line.startswith('data:'):
                        data_str = line[5:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            obj = json.loads(data_str)
                            # 多种可能位置提取增量文本
                            delta = (
                                obj.get('choices', [{}])[0]
                                   .get('delta', {})
                                   .get('content')
                            )
                            if not delta:
                                delta = (
                                    obj.get('choices', [{}])[0]
                                       .get('message', {})
                                       .get('content')
                                )
                            if not delta:
                                delta = obj.get('content')
                        except Exception:
                            delta = None
                        if delta:
                            yield delta
                    else:
                        # 某些服务直接返回纯文本分块
                        yield line
    except Exception as e:
        logger.error(f"stream call failed: {str(e)}")
        # 失败时不抛出，避免中断外层SSE，交由调用方处理
        return

@app.post("/generate/stream")
async def generate_prompt_stream(
    task: Task,
    current_user = Depends(get_current_user)
):
    """兼容旧路径：与 /generate?stream=true 等价。"""
    # 权限校验（与 /generate 一致）
    project = await supabase_db.get_project(task.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    if project["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="没有权限访问此项目")
    headers = {
        "Cache-Control": "no-cache, no-transform",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive"
    }
    return StreamingResponse(
        _generate_sse_generator(task, current_user)(),
        media_type="text/event-stream",
        headers=headers
    )

@app.post("/test")
async def test_prompt(
    request: TestRequest,
    current_user: UserInfo = Depends(get_current_user)
):
    """测试提示词"""
    try:
        logger.info(f"测试提示词: 用户ID: {current_user.id}, 项目ID: {request.project_id}")
        
        # 检查项目是否存在
        project = await supabase_db.get_project(request.project_id)
        if not project:
            raise HTTPException(status_code=404, detail="项目不存在")
            
        # 检查项目权限
        if project["user_id"] != current_user.id:
            raise HTTPException(status_code=403, detail="没有权限访问此项目")
        
        # 构建消息（支持 system + 多条 user 消息）
        messages = []
        sys_content = (request.system_prompt or "").strip()
        if sys_content:
            messages.append({"role": "system", "content": sys_content})
        # 构建 user 消息列表，支持多条消息和多模态（图片）
        user_messages = build_user_messages(request)
        messages.extend(user_messages)
        
        # 调用API
        try:
            response = await create_chat_completion(request.model, messages, request.max_tokens)
            logger.info(f"API响应类型: {type(response)}")
            
            # 提取响应内容
            result = extract_test_response(response)
            logger.info(f"提取的响应内容长度: {len(result)}")
            logger.debug(f"提取的响应内容: {result[:500]}...")  # 只记录前500个字符
            
            return {"result": result}
        except Exception as e:
            logger.error(f"API调用失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"API调用失败: {str(e)}")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"测试提示词失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/test/stream")
async def test_prompt_stream(
    request: TestRequest,
    current_user: UserInfo = Depends(get_current_user)
):
    """测试提示词（流式SSE）。不保存历史，仅实时返回模型输出。
    前端将按增量渲染，最终用 done payload 覆盖最终结果。
    """
    try:
        logger.info(f"测试提示词(流式): 用户ID: {current_user.id}, 项目ID: {request.project_id}")
        
        # 调试日志：记录接收到的请求内容
        logger.info(f"[DEBUG] system_prompt 长度: {len(request.system_prompt) if request.system_prompt else 0}")
        logger.info(f"[DEBUG] user_prompt: {request.user_prompt[:100] if request.user_prompt else 'None'}...")
        logger.info(f"[DEBUG] images 数量: {len(request.images) if request.images else 0}")
        logger.info(f"[DEBUG] user_messages 数量: {len(request.user_messages) if request.user_messages else 0}")
        if request.user_messages:
            for i, msg in enumerate(request.user_messages):
                logger.info(f"[DEBUG] user_messages[{i}].content 数量: {len(msg.content) if msg.content else 0}")
                logger.info(f"[DEBUG] user_messages[{i}].text: {msg.text[:100] if msg.text else 'None'}...")
                logger.info(f"[DEBUG] user_messages[{i}].images 数量: {len(msg.images) if msg.images else 0}")
                if msg.content:
                    for j, part in enumerate(msg.content):
                        if part.type == "text":
                            logger.info(f"[DEBUG] content[{j}]: type=text, text={part.text[:50] if part.text else 'None'}...")
                        elif part.type == "image_url":
                            url_preview = str(part.image_url)[:80] if part.image_url else 'None'
                            logger.info(f"[DEBUG] content[{j}]: type=image_url, url={url_preview}...")
        # 检查项目是否存在
        project = await supabase_db.get_project(request.project_id)
        if not project:
            raise HTTPException(status_code=404, detail="项目不存在")
        # 检查项目权限
        if project["user_id"] != current_user.id:
            raise HTTPException(status_code=403, detail="没有权限访问此项目")

        async def sse_test_generator():
            accumulated = ""
            # 上游流式
            # 组装消息（支持 system + 多条 user 消息）
            sys_content = (request.system_prompt or "").strip()
            messages = []
            if sys_content:
                messages.append({"role": "system", "content": sys_content})
            
            # 构建 user 消息列表，支持多条消息和多模态（图片）
            user_messages = build_user_messages(request)
            messages.extend(user_messages)

            async for delta in create_chat_completion_stream(
                model=request.model,
                messages=messages,
                max_tokens=request.max_tokens
            ):
                if not delta:
                    continue
                accumulated += delta
                # 直接把增量推给前端
                yield f"data: {json.dumps({'delta': delta})}\n\n"

            # 完成事件，返回与非流式相同结构字段名
            result_obj = {"result": accumulated}
            yield "event: done\n" + f"data: {json.dumps(result_obj)}\n\n"

        headers = {
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
        return StreamingResponse(sse_test_generator(), media_type="text/event-stream", headers=headers)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"测试提示词(流式)失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
def extract_test_response(response) -> str:
    """提取测试响应中的实际内容，增强处理各种响应格式的能力"""
    try:
        logger.debug(f"API响应原始内容类型: {type(response)}")
        logger.debug(f"API响应内容: {str(response)[:1000]}")  # 记录响应内容的前1000个字符
        
        # 处理对象类型的响应
        if isinstance(response, dict):
            logger.debug(f"处理字典类型响应，键: {list(response.keys())}")
            
            # 处理混元API格式 (Response.Choices[0].Message.Content)
            if "Response" in response:
                logger.debug("检测到混元API格式")
                # 记录完整的响应结构以便调试
                logger.debug(f"完整混元响应: {json.dumps(response, ensure_ascii=False)[:1000]}")
                
                # 从Response字段获取数据
                resp_data = response.get("Response", {})
                
                # 处理混元不同格式的响应
                if "Choices" in resp_data and isinstance(resp_data["Choices"], list) and len(resp_data["Choices"]) > 0:
                    choices = resp_data["Choices"]
                    message = choices[0].get("Message", {})
                    if "Content" in message:
                        content = message["Content"]
                        logger.debug(f"从混元API格式提取的内容长度: {len(content)}")
                        return fix_unicode_escapes(content.strip())
                elif "ResponseText" in resp_data:
                    # 有些混元API可能直接返回ResponseText
                    content = resp_data["ResponseText"]
                    logger.debug(f"从混元API ResponseText提取的内容长度: {len(content)}")
                    return fix_unicode_escapes(content.strip())
                elif "RequestId" in resp_data:
                    # 只有RequestId但没有Content的情况
                    logger.warning(f"混元API响应中仅有RequestId，可能出现错误: {resp_data.get('RequestId', '')}")
                    # 尝试从Response整体获取有用内容
                    if isinstance(resp_data, dict):
                        return json.dumps(resp_data, ensure_ascii=False)
            
            # 处理302ai API格式（choices.message.content）
            if "choices" in response and response["choices"]:
                logger.debug("检测到302ai API格式")
                choice = response["choices"][0]
                if isinstance(choice, dict):
                    if "message" in choice and isinstance(choice["message"], dict):
                        content = choice["message"].get("content", "")
                        if content:
                            logger.debug(f"从302ai API格式提取的内容长度: {len(content)}")
                            return fix_unicode_escapes(content.strip())
            
            # 处理302ai API特定的content列表格式
            if "content" in response and isinstance(response["content"], list):
                logger.debug("检测到302ai content列表格式")
                full_text = ""
                for item in response["content"]:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text = item.get("text", "")
                        if isinstance(text, bytes):
                            text = text.decode('utf-8', errors='replace')
                        full_text += text
                
                if full_text:
                    logger.debug(f"从content列表提取的文本长度: {len(full_text)}")
                    # 提取product_description标签内容
                    try:
                        matches = re.findall(r'<product_description>(.*?)</product_description>', full_text, re.DOTALL | re.IGNORECASE)
                        if matches:
                            return matches[0].strip()
                    except Exception as e:
                        logger.error(f"提取标签内容失败: {str(e)}")
                    return full_text.strip()
            
            # 如果无法找到预期的字段，返回完整的JSON
            logger.warning(f"无法从响应中找到预期字段，返回完整JSON")
            return json.dumps(response, ensure_ascii=False)
            
        # 处理字符串类型的响应
        elif isinstance(response, str):
            logger.debug("处理字符串类型响应")
            return fix_unicode_escapes(response.strip())
        
        # 处理bytes类型
        elif isinstance(response, bytes):
            logger.debug("处理bytes类型响应")
            try:
                decoded = response.decode('utf-8', errors='replace').strip()
                return fix_unicode_escapes(decoded)
            except Exception as e:
                logger.error(f"解码bytes失败: {str(e)}")
                return response.decode('latin1', errors='replace').strip()
                
        # 其他类型转为字符串
        logger.debug(f"处理其他类型响应: {type(response)}")
        return str(response)
    except Exception as e:
        logger.error(f"Error extracting test response: {str(e)}")
        # 在错误情况下，尝试以最原始的方式返回响应
        try:
            if isinstance(response, dict):
                return json.dumps(response, ensure_ascii=False)
            elif isinstance(response, bytes):
                return response.decode('utf-8', errors='replace')
            return str(response)
        except Exception as final_error:
            logger.error(f"最终提取失败: {str(final_error)}")
            return "无法提取响应内容"

def fix_unicode_escapes(text):
    """修复Unicode和十六进制转义序列"""
    if not isinstance(text, str):
        logger.warning(f"fix_unicode_escapes接收到非字符串类型: {type(text)}")
        try:
            if isinstance(text, bytes):
                text = text.decode('utf-8', errors='replace')
            else:
                text = str(text)
        except Exception as e:
            logger.error(f"转换为字符串失败: {str(e)}")
            return str(text)
    
    # 如果没有转义序列，直接返回
    if '\\x' not in text and '\\u' not in text and '%' not in text:
        return text
    
    try:
        # 尝试修复不同类型的编码问题
        
        # 1. 处理 \uXXXX 格式
        def replace_unicode(match):
            try:
                code = match.group(1)
                if len(code) == 4:  # \uXXXX 格式
                    return chr(int(code, 16))
                return match.group(0)
            except Exception as e:
                logger.warning(f"Unicode替换失败: {str(e)}")
                return match.group(0)
        
        # 2. 处理 \xXX 格式
        def replace_hex(match):
            try:
                code = match.group(1)
                if len(code) == 2:  # \xXX 格式
                    return bytes.fromhex(code).decode('utf-8')
                return match.group(0)
            except Exception as e:
                logger.warning(f"Hex替换失败: {str(e)}")
                return match.group(0)
        
        # 3. 处理URL编码 %XX 格式
        def replace_url_encoding(match):
            try:
                code = match.group(1)
                if len(code) == 2:  # %XX 格式
                    return bytes.fromhex(code).decode('utf-8')
                return match.group(0)
            except Exception as e:
                logger.warning(f"URL编码替换失败: {str(e)}")
                return match.group(0)
        
        # 先处理 \uXXXX 格式
        fixed_text = re.sub(r'\\u([0-9a-fA-F]{4})', replace_unicode, text)
        # 再处理 \xXX 格式
        fixed_text = re.sub(r'\\x([0-9a-fA-F]{2})', replace_hex, fixed_text)
        # 再处理 %XX 格式
        fixed_text = re.sub(r'%([0-9a-fA-F]{2})', replace_url_encoding, fixed_text)
        
        # 检查是否有明显的乱码字符（替换字符或控制字符）
        if '\ufffd' in fixed_text or any(ord(c) < 32 and c not in '\r\n\t' for c in fixed_text):
            logger.debug("检测到可能的乱码，尝试其他修复方法")
            
            # 方法1: latin1 -> utf-8 转换
            try:
                latin1_fixed = text.encode('latin1').decode('utf-8', errors='replace')
                if not any(c == '\ufffd' for c in latin1_fixed):
                    logger.debug("latin1 -> utf-8转换成功")
                    return latin1_fixed
            except Exception as e:
                logger.error(f"latin1到utf-8转换失败: {str(e)}")
            
            # 方法2: 尝试JSON解析（处理双重转义）
            try:
                # 尝试解析JSON字符串，处理双重转义的情况
                import json
                # 将转义字符处理为JSON字符串格式
                json_str = '"' + text.replace('"', '\\"') + '"'
                json_fixed = json.loads(json_str)
                if not any(c == '\ufffd' for c in json_fixed):
                    logger.debug("JSON解析修复成功")
                    return json_fixed
            except Exception as e:
                logger.debug(f"JSON解析修复失败: {str(e)}")
            
            # 方法3: 移除无效字符
            try:
                # 移除所有控制字符和替换字符
                cleaned_text = ''.join(c for c in fixed_text if ord(c) >= 32 or c in '\r\n\t')
                logger.debug("移除了无效字符")
                return cleaned_text
            except Exception as e:
                logger.error(f"移除无效字符失败: {str(e)}")
        
        # 如果修复后的文本看起来合理，使用它
        if not any(c == '\ufffd' for c in fixed_text):
            return fixed_text
        
        # 如果所有方法都失败，返回原始文本
        logger.warning("所有修复方法都失败，返回原始文本")
        return text
    except Exception as e:
        logger.error(f"修复编码失败: {str(e)}")
        return text

def remove_empty_tags(text: str) -> str:
    """移除空的XML标签"""
    try:
        return re.sub(r'\n<(\w+)>\s*</\1>\n', '', text, flags=re.DOTALL)
    except Exception as e:
        logger.error(f"移除空标签出错: {str(e)}")
        return text

def strip_last_sentence(text: str) -> str:
    """移除最后的无用句子"""
    try:
        sentences = text.split('. ')
        if sentences[-1].startswith("Let me know"):
            sentences = sentences[:-1]
            result = '. '.join(sentences)
            if result and not result.endswith('.'):
                result += '.'
            return result
        return text
    except Exception as e:
        logger.error(f"处理句子出错: {str(e)}")
        return text

def extract_prompt(response: str) -> str:
    """从API响应中提取提示词模板
    
    Args:
        response: API响应文本
        
    Returns:
        提取的提示词模板
    """
    try:
        if not response or not response.strip():
            logger.warning("API响应为空")
            return ""
            
        matches = extract_between_tags("Instructions", response)
        logger.info(f"extract_prompt: 查找Instructions标签，找到 {len(matches) if matches else 0} 个匹配")
        if not matches:
            logger.warning("未找到<Instructions>标签，返回完整响应")
            logger.debug(f"响应内容前500字符: {response[:500]}...")
            return response.strip()
            
        content = matches[0]
        # 处理长文本
        if len(content) > 1000:
            first_part = content[:1000]
            second_part = content[1000:]
            second_part = remove_empty_tags(remove_empty_tags(second_part).strip())
            second_part = strip_last_sentence(second_part.strip())
            return first_part + second_part
        
        return strip_last_sentence(remove_empty_tags(content.strip()))
        
    except Exception as e:
        logger.error(f"提取提示词出错: {str(e)}")
        return ""

@app.post("/api/prompts/{prompt_id}/refresh-variables")
async def refresh_prompt_variables(
    prompt_id: str,
    current_user: UserInfo = Depends(get_current_user)
):
    logger.info(f"刷新提示词变量: 提示词ID: {prompt_id}, 用户ID: {current_user.id}")
    
    try:
        # 获取提示词内容
        prompt = db.get_prompt(prompt_id)
        if not prompt:
            raise HTTPException(status_code=404, detail="Prompt not found")
            
        # 重新提取变量
        variables = list(extract_variables(prompt["content"]))
        
        # 更新数据库
        db.update_prompt_variables(prompt_id, variables)
        
        return {"success": True, "variables": variables}
    except Exception as e:
        logger.error(f"Refresh variables failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/prompts/{prompt_id}")
async def update_prompt(
    prompt_id: str,
    request: dict,
    current_user: UserInfo = Depends(get_current_user)
):
    """更新现有提示词（不创建新版本）"""
    logger.info(f"更新提示词内容: 提示词ID: {prompt_id}, 用户ID: {current_user.id}")
    
    try:
        # 获取当前提示词（使用prompt_history表）
        prompt = await supabase_db.get_prompt_history_by_id(prompt_id)
        if not prompt:
            raise HTTPException(status_code=404, detail="提示词不存在")
        
        # 检查权限（通过检查项目所有权）
        project = await supabase_db.get_project(prompt["project_id"])
        if not project:
            raise HTTPException(status_code=404, detail="项目不存在")
            
        if project["user_id"] != current_user.id:
            logger.warning(f"用户 {current_user.id} 尝试更新不属于他的提示词 {prompt_id}")
            raise HTTPException(status_code=403, detail="您没有权限更新此提示词")
        
        # 支持新格式（system_prompt + user_prompt）和旧格式（content）
        system_prompt = request.get("system_prompt") or request.get("content")
        user_prompt = request.get("user_prompt", "")
        variables = request.get("variables", [])
        
        if not system_prompt:
            raise HTTPException(status_code=400, detail="提示词内容不能为空")
        
        # 如果没有传入变量，则提取变量
        if not variables:
            variables = list(extract_variables(system_prompt))
            if user_prompt:
                variables.extend(list(extract_variables(user_prompt)))
                variables = list(set(variables))  # 去重
        
        # 直接更新数据库记录
        try:
            admin_client = supabase_db.get_admin_client()
            if admin_client:
                update_data = {
                    "system_prompt": system_prompt,
                    "user_prompt": user_prompt,
                    "variables": {"variables": variables}
                }
                result = admin_client.table("prompt_history") \
                    .update(update_data) \
                    .eq("id", prompt_id) \
                    .execute()
                
                if result.data:
                    updated_prompt = result.data[0]
                    logger.info(f"已更新提示词 {prompt_id}")
                else:
                    raise HTTPException(status_code=500, detail="更新提示词失败")
            else:
                raise HTTPException(status_code=500, detail="数据库连接失败")
        except Exception as db_error:
            logger.error(f"更新数据库失败: {str(db_error)}")
            raise HTTPException(status_code=500, detail=f"更新失败: {str(db_error)}")
        
        return {
            "success": True,
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "variables": variables,
            "id": prompt_id,
            "version": updated_prompt.get("version", prompt.get("version"))
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新提示词失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新提示词失败: {str(e)}")

@app.post("/api/prompts")
async def save_prompt(
    request: SavePromptRequest,
    current_user: UserInfo = Depends(get_current_user)
):
    logger.info(f"保存提示词: 项目ID: {request.project_id}, 用户ID: {current_user.id}")
    
    try:
        # 先检查项目是否属于当前用户
        existing_project = await supabase_db.get_project(request.project_id)
        if not existing_project:
            raise HTTPException(status_code=404, detail="项目不存在")
            
        if existing_project.get("user_id") != current_user.id:
            logger.warning(f"用户 {current_user.id} 尝试在不属于他的项目 {request.project_id} 中创建提示词")
            raise HTTPException(status_code=403, detail="您没有权限在此项目中创建提示词")
        
        # 获取当前最大版本号
        latest_version = await supabase_db.get_latest_prompt_version(request.project_id) or 0
        
        # 构造历史记录数据 (支持 system_prompt 和 user_prompt)
        history_data = {
            "project_id": request.project_id,
            "system_prompt": request.system_prompt,
            "user_prompt": request.user_prompt or "",
            "version": latest_version + 1,
            "user_id": current_user.id,
            "change_summary": "Saved optimized prompt",
            "variables": {
                "variables": request.variables
            }
        }
        
        # 保存到历史记录
        prompt_history = await supabase_db.create_prompt_history(**history_data)
        if not prompt_history:
            logger.error("提示词历史记录创建失败")
            raise HTTPException(status_code=500, detail="提示词创建失败")
        
        logger.debug(f"成功创建提示词: {prompt_history['id']}")
        
        return {
            "success": True,
            "prompt": prompt_history
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"保存提示词失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"保存提示词失败: {str(e)}")

@app.post("/improve")
async def improve_prompt(
    request: ImproveRequest,
    current_user: UserInfo = Depends(get_current_user)
):
    try:
        logger.info(f"改进提示词: 项目ID: {request.project_id}, 提示词ID: {request.prompt_id}, 用户ID: {current_user.id}")
        
        # 检查项目是否存在
        project = await supabase_db.get_project(request.project_id)
        if not project:
            logger.error(f"项目不存在: {request.project_id}")
            raise HTTPException(status_code=404, detail="项目不存在")
            
        # 检查项目权限
        if project["user_id"] != current_user.id:
            logger.error(f"用户 {current_user.id} 没有权限访问项目 {request.project_id}")
            raise HTTPException(status_code=403, detail="没有权限访问此项目")
        
        # 将 request.model_dump() 改为 request.dict()
        logger.debug(f"Received improve request: {request.dict()}")
        
        # 一次性替换所有变量,直接使用 improveprompt.txt 作为提示词
        messages = [{
            "role": "user",
            "content": CACHED_IMPROVEPROMPT.replace(
                "{{IMPROVE INSTRUCTIONS}}", request.improve_instructions
            ).replace(
                "{{METAPROMPT}}", request.metaprompt
            ).replace(
                "{{EXAMPLE}}", ""  # 暂时传空字符串
            )
        }]
        
        logger.debug(f"Constructed messages: {messages}")
        
        # 调用 API
        try:
            response = await create_chat_completion(messages=messages)
            logger.debug(f"API response: {response}")
        except Exception as e:
            logger.error(f"API call failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"API调用失败: {str(e)}")
        
        # 提取规划和提示词
        planning = extract_between_tags("Planning initial draft", response)
        if not planning:
            logger.error(f"No planning found in response: {response}")
            raise HTTPException(status_code=400, detail="No planning generated")
            
        writing_prompts = extract_between_tags("Writing prompts", response)
        if not writing_prompts:
            logger.error(f"No writing prompts found in response: {response}")
            raise HTTPException(status_code=400, detail="No writing prompts generated")
        
        # 处理浮动变量 - 添加此逻辑
        processed_prompt = await process_floating_variables(writing_prompts[0])
        logger.info("提示词浮动变量处理完成")
        
        # 从优化后并处理过浮动变量的提示词中提取变量
        variables = list(extract_variables(processed_prompt))
        logger.debug(f"Extracted variables: {variables}")
        
        # 返回结果，不再自动保存到数据库
        return {
            "planning": planning[0],
            "writing_prompts": processed_prompt,
            "variables": variables
        }
        
    except HTTPException:
        # 直接重新抛出HTTP异常，以保持原始状态码和详情
        raise
    except Exception as e:
        logger.error(f"Improve prompt failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def process_floating_variables(prompt: str) -> str:
    """处理提示词中的浮动变量(包装函数)
    
    Args:
        prompt: 要处理的提示词文本
        
    Returns:
        处理后的提示词文本
    """
    try:
        floating_variables = find_free_floating_variables(prompt)
        if floating_variables:
            logger.info(f"Found floating variables: {floating_variables}")
            return await remove_inapt_floating_variables(prompt)
        return prompt
    except Exception as e:
        logger.error(f"Error processing floating variables: {str(e)}")
        return prompt

@app.post("/revise")
async def revise_prompt(
    request: ReviseRequest,
    current_user: UserInfo = Depends(get_current_user)
):
    try:
        logger.info(f"修改提示词: 项目ID: {request.project_id}, 用户ID: {current_user.id}")
        
        logger.debug("="*50)
        # 将 request.model_dump() 改为 request.dict()
        logger.debug(f"Received revise request: {request.dict()}")
        logger.debug("="*50)
        
        # 构建消息前先记录模板内容
        logger.debug(f"Original template content: {CACHED_REVISE_PLAN_PROMPT}")
        logger.debug("="*50)
        
        # 记录每个变量的值
        logger.debug(f"improve_instructions: {request.improve_instructions}")
        logger.debug(f"planning: {request.planning}")
        logger.debug(f"prompt: {request.prompt}")
        logger.debug("="*50)
        
        # 构建消息并记录替换后的内容
        content = CACHED_REVISE_PLAN_PROMPT.replace(
            "{{IMPROVE INSTRUCTIONS}}", request.improve_instructions
        ).replace(
            "{{PLANNING INITIAL DRAFT}}", request.planning
        ).replace(
            "{{WRITE PROMPTS}}", request.prompt
        )
        
        logger.debug(f"Template after replacement: {content}")
        logger.debug("="*50)
        
        messages = [{
            "role": "user",
            "content": content
        }]
        
        # 调用 API
        try:
            response = await create_chat_completion(messages=messages)
            logger.debug(f"API response: {response}")
        except Exception as e:
            logger.error(f"API call failed: {str(e)}")
            raise
        
        # 提取修改计划和最终提示词（使用正确的标签名）
        modification_plan = extract_between_tags("Modification plan analysis", response)
        if not modification_plan:
            logger.error(f"No modification plan found in response: {response}")
            raise HTTPException(status_code=400, detail="No modification plan generated")
            
        final_prompt = extract_between_tags("final draft prompt", response)
        if not final_prompt:
            logger.warning("No final draft prompt tags found, trying to extract content after modification plan")
            try:
                # 找到</Modification plan analysis>的位置
                end_mod_plan = response.find("</Modification plan analysis>")
                if end_mod_plan != -1:
                    # 获取之后的内容
                    remaining_content = response[end_mod_plan + len("</Modification plan analysis>"):].strip()
                    # 如果内容以<final draft prompt>开头，去掉这个标签
                    if remaining_content.startswith("<final draft prompt>"):
                        remaining_content = remaining_content[len("<final draft prompt>"):].strip()
                    # 如果内容以</final draft prompt>结尾，去掉这个标签
                    if remaining_content.endswith("</final draft prompt>"):
                        remaining_content = remaining_content[:-len("</final draft prompt>")].strip()
                    final_prompt = [remaining_content]
                else:
                    raise ValueError("Could not find end of modification plan")
            except Exception as e:
                logger.error(f"Error extracting final prompt: {str(e)}")
                raise HTTPException(status_code=400, detail="Could not extract final prompt")
        
        if not final_prompt:
            logger.error(f"No final prompt found in response: {response}")
            raise HTTPException(status_code=400, detail="No final prompt generated")
            
        # 处理浮动变量 - 添加此逻辑
        processed_prompt = await process_floating_variables(final_prompt[0])
        logger.info("提示词浮动变量处理完成")
            
        # 提取变量（从处理后的提示词中提取）
        variables = list(extract_variables(processed_prompt))
        
        # 直接返回结果，不保存到数据库
        return {
            "modification_plan": modification_plan[0],
            "final_prompt": processed_prompt,
            "variables": variables
        }
            
    except Exception as e:
        logger.error(f"Revise prompt failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/projects/{project_id}/prompts/{history_id}")
async def get_prompt_version(
    project_id: str,
    history_id: str,
    current_user: UserInfo = Depends(get_current_user)
):
    """获取项目下的特定提示词版本
    
    Args:
        project_id: 项目ID
        history_id: 历史记录ID
        current_user: 当前用户
        
    Returns:
        特定版本的提示词内容
    """
    try:
        # 1. 检查项目是否存在且属于当前用户
        project = await supabase_db.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="项目不存在")
        if project["user_id"] != current_user.id:
            raise HTTPException(status_code=403, detail="没有权限访问此项目")
            
        # 2. 获取特定版本内容
        version = await supabase_db.get_prompt_history_by_id(history_id)
        if not version:
            raise HTTPException(status_code=404, detail="版本不存在")
        if version["project_id"] != project_id:
            raise HTTPException(status_code=400, detail="该版本不属于此项目")
            
        # 3. 返回版本内容（支持 system_prompt 和 user_prompt）
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": {
                    "id": version["id"],
                    # 向后兼容：同时返回 content 和 system_prompt
                    "content": version.get("system_prompt") or version.get("content", ""),
                    "system_prompt": version.get("system_prompt") or version.get("content", ""),
                    "user_prompt": version.get("user_prompt", ""),
                    "version": version["version"],
                    "variables": version["variables"].get("variables", []) if version["variables"] else [],
                    "created_at": version["created_at"],
                    "change_summary": version.get("change_summary", "")
                }
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取提示词版本失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 获取提示词的所有版本列表
@app.get("/api/projects/{project_id}/prompts/{prompt_id}/versions")
async def get_prompt_versions(
    project_id: str,
    prompt_id: str,
    request: VersionListRequest = Depends(),
    current_user: UserInfo = Depends(get_current_user)
):
    """获取提示词的所有历史版本列表
    
    Args:
        project_id: 项目ID
        prompt_id: 提示词ID
        request: 分页和排序参数
        current_user: 当前用户
        
    Returns:
        提示词历史版本列表，包含分页信息
    """
    try:
        # 1. 检查项目是否存在且属于当前用户
        project = await supabase_db.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="项目不存在")
        if project["user_id"] != current_user.id:
            raise HTTPException(status_code=403, detail="没有权限访问此项目")
            
        # 2. 检查提示词是否存在且属于该项目
        prompt = await supabase_db.get_prompt(prompt_id)
        if not prompt:
            raise HTTPException(status_code=404, detail="提示词不存在")
        if prompt["project_id"] != project_id:
            raise HTTPException(status_code=400, detail="提示词不属于该项目")
            
        # 3. 获取历史版本总数
        total_versions = await supabase_db.count_prompt_versions(prompt_id)
        
        # 4. 计算分页
        offset = (request.page - 1) * request.page_size
        
        # 5. 获取历史版本列表
        versions = await supabase_db.get_prompt_versions(
            prompt_id=prompt_id,
            limit=request.page_size,
            offset=offset,
            sort_by=request.sort_by,
            sort_order=request.sort_order
        )
        
        # 6. 格式化返回数据
        return {
            "success": True,
            "data": {
                "versions": versions,
                "pagination": {
                    "current_page": request.page,
                    "page_size": request.page_size,
                    "total_pages": (total_versions + request.page_size - 1) // request.page_size,
                    "total_items": total_versions
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取提示词历史版本列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def generate_prompt_template(task: str) -> str:
    """生成提示词模板
    
    Args:
        task: 用户的任务描述
        
    Returns:
        生成的提示词模板
    """
    try:
        logger.info(f"开始生成提示词模板，任务描述长度: {len(task)}字符")
        # 使用缓存的metaprompt，替换任务描述
        prompt = CACHED_METAPROMPT.replace("{{TASK}}", task)
        
        # 如果任务描述过长，可能导致超时，尝试截断
        if len(task) > 3000:
            logger.warning(f"任务描述过长({len(task)}字符)，截断至3000字符")
            task_truncated = task[:3000] + "..."
            prompt = CACHED_METAPROMPT.replace("{{TASK}}", task_truncated)
        
        logger.info("调用API生成提示词模板...")
        # 调用API生成提示词模板
        response = await create_chat_completion(
            messages=[{
                "role": "user",
                "content": prompt
            }],
            max_retries=3
        )
        logger.info(f"API调用成功，返回内容长度: {len(response)}字符")
        
        # 提取生成的提示词模板
        template = extract_prompt(response)
        if not template:
            logger.error("无法从API响应中提取提示词模板")
            raise Exception("无法从API响应中提取提示词模板")
        
        logger.info(f"成功生成提示词模板，长度: {len(template)}字符")
        return template
        
    except Exception as e:
        logger.error(f"生成提示词模板失败: {str(e)}", exc_info=True)
        raise

# 添加API测试路由
@app.get("/api-test")
async def api_test_page():
    """API测试页面"""
    return FileResponse(os.path.join(BASE_DIR, "static", "api_test.html"))

@app.post("/test-api")
async def test_api(request: Request, current_user: UserInfo = Depends(get_current_user)):
    """测试API连接（消耗服务端 LLM 配额，需登录）"""
    try:
        # 获取请求body
        body = await request.json()
        model = body.get("model", MODEL_NAME)
        prompt = body.get("prompt", "你好，这是一个API测试。")
        
        logger.info(f"API测试 - 模型: {model}, 提示: {prompt}")
        
        # 调用API
        response = await create_chat_completion(
            model=model,
            messages=[{
                "role": "user",
                "content": prompt
            }],
            max_tokens=100,
            max_retries=2
        )
        
        # 解析响应
        return JSONResponse({
            "success": True,
            "model": model,
            "response": response,
            "timestamp": str(datetime.datetime.now())
        })
        
    except Exception as e:
        logger.error(f"API测试失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "timestamp": str(datetime.datetime.now())
            }
        )

@app.get("/check-config")
async def check_config(current_user: UserInfo = Depends(get_current_user)):
    """检查配置（会暴露 API 地址等信息，需登录）"""
    try:
        return {
            "api_key_set": bool(API_KEY),
            "api_key_length": len(API_KEY) if API_KEY else 0,
            "api_url": API_URL,
            "model_name": MODEL_NAME,
            "available_models": AVAILABLE_MODELS.split(",") if AVAILABLE_MODELS else [],
            "environment": "Vercel" if os.environ.get('VERCEL', False) else "Local",
            "timestamp": str(datetime.datetime.now())
        }
    except Exception as e:
        logger.error(f"检查配置失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "timestamp": str(datetime.datetime.now())
            }
        )

if __name__ == "__main__":
    import uvicorn
    import sys
    
    def find_free_port():
        """找到一个可用的端口"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', 0))
            return s.getsockname()[1]
    
    # 检查是否在Vercel环境中运行
    is_vercel = os.environ.get('VERCEL', False)
    
    if is_vercel:
        # Vercel环境中不需要启动服务器
        print("在Vercel环境中运行，不启动独立服务器")
    else:
        try:
            # 优先使用环境变量指定的端口，否则自动寻找空闲端口
            port = int(os.environ.get("PORT", "0"))
            if port == 0:
                port = find_free_port()
                
            print(f"===================================================")
            print(f"服务器将在 http://127.0.0.1:{port} 启动")
            print(f"===================================================")
            
            # 启动服务器
            uvicorn.run(app, host="127.0.0.1", port=port)
        except Exception as e:
            print(f"启动服务器时出错: {str(e)}")
            sys.exit(1)
