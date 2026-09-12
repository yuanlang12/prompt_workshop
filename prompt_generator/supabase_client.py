"""
Supabase客户端配置与初始化
"""

import os
import logging
from supabase import create_client, Client

# 配置日志
logger = logging.getLogger(__name__)

# 直接从环境变量获取Supabase配置
# 在生产环境（如Vercel），这些环境变量应该在平台上设置
# 对于本地开发，从settings.py导入（包含默认值）
try:
    # 优先检查系统环境变量是否已存在
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
    SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    
    # 如果环境变量不存在，则尝试从settings.py获取
    if not SUPABASE_URL or not SUPABASE_KEY:
        from config.settings import SUPABASE_URL, SUPABASE_KEY, SUPABASE_SERVICE_ROLE_KEY
        logger.info("从config.settings导入Supabase配置成功")
except ImportError:
    logger.error("无法导入config.settings模块，Supabase配置可能不完整")
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
    SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

# 初始化Supabase客户端
supabase: Client = None

def init_supabase():
    """初始化Supabase客户端"""
    global supabase
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("Supabase配置不完整，请检查环境变量")
        return None
    
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("Supabase客户端初始化成功")
        return supabase
    except Exception as e:
        logger.error(f"Supabase客户端初始化失败: {str(e)}")
        return None

def get_supabase_admin_client():
    """获取具有管理员权限的Supabase客户端（用于数据迁移等操作）"""
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        logger.error("Supabase管理员配置不完整，请检查环境变量")
        return None
    
    try:
        admin_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        logger.info("Supabase管理员客户端初始化成功")
        return admin_client
    except Exception as e:
        logger.error(f"Supabase管理员客户端初始化失败: {str(e)}")
        return None

# 在模块导入时自动初始化客户端
supabase = init_supabase() 