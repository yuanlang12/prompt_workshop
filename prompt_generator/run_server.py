import socket
import uvicorn
import os
import sys

# 确保能够导入server模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def find_free_port():
    """找到一个可用的端口"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]

if __name__ == "__main__":
    try:
        # 优先使用环境变量指定的端口，否则使用默认的8000端口
        port = int(os.getenv("PORT", "8000"))
        
        # 检查端口是否可用
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
        except OSError:
            # 如果端口被占用，找一个可用端口
            print(f"端口 {port} 已被占用，正在寻找可用端口...")
            port = find_free_port()
        
        print(f"===================================================")
        print(f"服务器将在 http://127.0.0.1:{port} 启动")
        print(f"===================================================")
        
        # 启动服务器
        from server import app
        uvicorn.run(app, host="127.0.0.1", port=port)
    except Exception as e:
        print(f"启动服务器时出错: {str(e)}")
        sys.exit(1) 