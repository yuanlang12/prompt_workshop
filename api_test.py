import aiohttp
import asyncio
import json
import os
import sys

# 从.env文件加载API密钥
try:
    with open("prompt_generator/config/.env", "r", encoding="utf-8") as f:
        lines = f.readlines()
        for line in lines:
            if line.startswith("API_KEY="):
                os.environ["API_KEY"] = line.strip().split("=")[1]
            if line.startswith("API_URL="):
                os.environ["API_URL"] = line.strip().split("=")[1]
            if line.startswith("MODEL_NAME="):
                os.environ["MODEL_NAME"] = line.strip().split("=")[1]
    print(f"成功从.env文件加载配置")
except Exception as e:
    print(f"加载.env文件失败: {str(e)}")

# 获取API配置
API_KEY = os.environ.get("API_KEY", "")
API_URL = os.environ.get("API_URL", "https://api.302.ai/v1/chat/completions")
MODEL_NAME = os.environ.get("MODEL_NAME", "deepseek-v3-huoshan")

print(f"API_KEY: {'*' * 8 + API_KEY[-4:] if API_KEY and len(API_KEY) > 4 else 'Not set'}")
print(f"API_URL: {API_URL}")
print(f"MODEL_NAME: {MODEL_NAME}")

# 创建简单的测试消息
test_message = "你好，这是一个API测试。请简短回复以确认连接正常。"

async def test_api():
    print("\n开始测试API连接...")
    
    # 测试不同的模型
    models_to_test = [
        MODEL_NAME,                # 默认模型
        "deepseek-v2-huoshan",     # 备选模型1
        "qwen-plus"                # 备选模型2
    ]
    
    for model in models_to_test:
        try:
            print(f"\n测试模型: {model}")
            
            # 构建请求
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {API_KEY}"
            }
            
            data = {
                "model": model,
                "messages": [{"role": "user", "content": test_message}],
                "max_tokens": 100
            }
            
            print(f"发送请求到: {API_URL}")
            print(f"请求数据: {json.dumps(data, ensure_ascii=False)}")
            
            # 发送请求
            timeout = aiohttp.ClientTimeout(total=30)  # 30秒超时
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(API_URL, headers=headers, json=data) as response:
                    print(f"响应状态码: {response.status}")
                    
                    if response.status == 200:
                        # 读取响应内容
                        response_text = await response.text()
                        print(f"响应内容(前100个字符): {response_text[:100]}...")
                        
                        # 尝试解析JSON
                        try:
                            result = json.loads(response_text)
                            print(f"成功解析JSON响应")
                            print(f"响应包含以下键: {list(result.keys())}")
                        except json.JSONDecodeError:
                            print(f"无法解析JSON响应")
                    else:
                        error_text = await response.text()
                        print(f"错误响应: {error_text[:200]}")
                        
        except Exception as e:
            print(f"测试模型 {model} 时出错: {str(e)}")
            print(f"错误类型: {type(e).__name__}")

        print(f"模型 {model} 测试完成")
        print("-" * 50)

# 运行测试
if __name__ == "__main__":
    asyncio.run(test_api()) 