import os
import logging

# 不在这里调用 logging.basicConfig，交由应用入口（server.py）统一配置，
# 否则会在入口配置 LOG_LEVEL 之前抢占全局日志配置
logger = logging.getLogger(__name__)

# 检查是否在Vercel环境中
IN_VERCEL = os.environ.get('VERCEL', 'False').lower() == 'true'
logger.debug(f"Running in Vercel environment: {IN_VERCEL}")

# 仅在非Vercel环境中加载dotenv
if not IN_VERCEL:
    try:
        from dotenv import load_dotenv
        # 获取当前文件所在目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        env_path = os.path.join(current_dir, '.env')
        
        # 记录 .env 文件路径
        logger.debug(f"Looking for .env file at: {env_path}")
        
        # 加载当前目录下的.env文件（本地开发环境）
        load_dotenv(env_path)
        logger.debug("Successfully loaded .env file")
    except ImportError:
        logger.warning("python-dotenv not installed, skipping .env file loading")
        pass

# 获取并记录配置值 - 优先使用系统环境变量
# API_URL 支持任何 OpenAI 兼容接口（OpenAI / DeepSeek / 302.ai / Ollama 等）
API_KEY = os.getenv("API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
API_URL = os.getenv("API_URL", "https://api.openai.com/v1/chat/completions")

# 获取可用模型列表（格式: model_id:显示名称,多个用英文逗号分隔）
AVAILABLE_MODELS = os.getenv("AVAILABLE_MODELS", "gpt-4o-mini:gpt-4o-mini,gpt-4o:gpt-4o")

# Supabase配置 - 仅从环境变量读取，不提供默认值
# 请在 config/.env（本地）或部署平台的环境变量中配置，
# 参考 config/.env.example 和 docs/supabase_setup.sql
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.warning(
        "Supabase 未配置：请在 config/.env 中设置 SUPABASE_URL 和 SUPABASE_KEY "
        "（可复制 config/.env.example），否则登录/注册和数据功能不可用"
    )
if not SUPABASE_SERVICE_ROLE_KEY:
    logger.warning(
        "SUPABASE_SERVICE_ROLE_KEY 未配置：数据读写（项目/提示词的增删改查）依赖该密钥，"
        "缺失时相关功能不可用"
    )

logger.debug(f"Loaded API_KEY: {'*' * len(API_KEY) if API_KEY else 'None'}")
logger.debug(f"Loaded MODEL_NAME: {MODEL_NAME}")
logger.debug(f"Loaded API_URL: {API_URL}")
logger.debug(f"Loaded AVAILABLE_MODELS: {AVAILABLE_MODELS}")
logger.debug(f"Loaded SUPABASE_URL: {SUPABASE_URL}")
logger.debug(f"Loaded SUPABASE_KEY: {'*' * len(SUPABASE_KEY) if SUPABASE_KEY else 'None'}")
logger.debug(f"Loaded SUPABASE_SERVICE_ROLE_KEY: {'*' * len(SUPABASE_SERVICE_ROLE_KEY) if SUPABASE_SERVICE_ROLE_KEY else 'None'}")