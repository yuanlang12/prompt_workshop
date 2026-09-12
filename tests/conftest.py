import os
import sys

# 让测试可以直接导入 prompt_generator 目录下的模块
sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "prompt_generator"),
)
