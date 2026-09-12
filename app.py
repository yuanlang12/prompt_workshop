# Vercel入口文件
import os
import sys

# 添加项目目录到 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))
prompt_generator_path = os.path.join(current_dir, "prompt_generator")

if not os.path.exists(prompt_generator_path):
    raise ImportError(f"Cannot find prompt_generator directory at {prompt_generator_path}")

# 添加项目路径到 Python 路径
sys.path.append(prompt_generator_path)

# 导入原始应用
from server import app 