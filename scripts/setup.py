#!/usr/bin/env python3
"""提示词工坊 一键安装与启动引导脚本

macOS 双击 start_mac.command、Windows 双击 start_windows.bat 即会运行本脚本：
创建虚拟环境 -> 安装依赖 -> 交互式生成 config/.env -> 启动服务并打开浏览器。
已配置过的情况下再次运行，会直接使用现有配置启动。
"""

import os
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP_DIR = ROOT / "prompt_generator"
CONFIG_DIR = APP_DIR / "config"
ENV_FILE = CONFIG_DIR / ".env"
VENV_DIR = ROOT / ".venv"
REQ_FILE = ROOT / "requirements.txt"
DEPS_STAMP = VENV_DIR / ".deps_stamp"

IS_WINDOWS = os.name == "nt"
VENV_PYTHON = VENV_DIR / ("Scripts\\python.exe" if IS_WINDOWS else "bin/python")

# 配置项: (env键名, 提示语, 默认值, 是否必填, 说明)
QUESTIONS = [
    ("SUPABASE_URL", "Supabase 项目地址", "", False,
     "在 https://supabase.com 创建项目后，Project Settings -> API 页面获取"),
    ("SUPABASE_KEY", "Supabase anon public key", "", False,
     "同上页面，anon public 一栏"),
    ("SUPABASE_SERVICE_ROLE_KEY", "Supabase service_role key", "", False,
     "同上页面，service_role 一栏（仅保存在本机/服务端，勿外传）"),
    ("API_URL", "LLM 接口地址 (OpenAI 兼容)", "https://api.openai.com/v1/chat/completions", False,
     "OpenAI / DeepSeek / 302.ai / Ollama 等均可"),
    ("API_KEY", "LLM API Key", "", False,
     "对应上方接口的密钥"),
    ("MODEL_NAME", "默认模型", "gpt-4o-mini", False,
     "如 gpt-4o-mini / deepseek-chat / qwen-max"),
    ("AVAILABLE_MODELS", "可选模型列表 (model_id:显示名称，逗号分隔)", "gpt-4o-mini:gpt-4o-mini,gpt-4o:gpt-4o", False,
     "直接回车使用默认值"),
]


def out(text=""):
    print(text, flush=True)


def die(message, hint=""):
    out(f"\n[错误] {message}")
    if hint:
        out(hint)
    out()
    if IS_WINDOWS:
        subprocess.run("pause", shell=True, check=False)
    sys.exit(1)


def ask(prompt, default="", required=False, hint=""):
    if hint:
        out(f"  （{hint}）")
    while True:
        value = input(f"{prompt}" + (f" [回车={default}]" if default else "") + ": ").strip()
        if not value and default:
            return default
        if value or not required:
            return value
        out("  不能为空，请重新输入")


def mask(value):
    if not value:
        return "(未配置)"
    return value[:6] + "..." if len(value) > 12 else value


def ensure_console():
    # Windows 控制台编码可能无法编码中文，降级为替换而非崩溃
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except Exception:
            pass


def ensure_venv():
    if not VENV_PYTHON.exists():
        out("首次运行：正在创建虚拟环境 ...")
        result = subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)])
        if result.returncode != 0 or not VENV_PYTHON.exists():
            die("创建虚拟环境失败", "请确认已安装 Python 3.9+ 后重试")
    if not DEPS_STAMP.exists() or DEPS_STAMP.stat().st_mtime < REQ_FILE.stat().st_mtime:
        out("正在安装依赖（首次约需 1~2 分钟）...")
        result = subprocess.run(
            [str(VENV_PYTHON), "-m", "pip", "install", "-q", "--disable-pip-version-check",
             "-r", str(REQ_FILE)]
        )
        if result.returncode != 0:
            die("依赖安装失败", "请检查网络后重新运行本脚本")
        DEPS_STAMP.write_text("ok")


def load_env_file(path):
    values = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                values[key.strip()] = val.strip()
    return values


def ensure_config():
    existing = load_env_file(ENV_FILE)
    if existing:
        out("\n检测到已有配置：")
        for key, _, _, _, _ in QUESTIONS:
            out(f"  {key} = {mask(existing.get(key, ''))}")
        choice = input("直接使用以上配置启动？（回车=是 / r=重新配置）: ").strip().lower()
        if choice != "r":
            return existing
    else:
        out("\n未检测到配置文件，开始首次配置。")
        out("提示：数据存储与用户登录使用 Supabase（免费），LLM 使用任意 OpenAI 兼容接口。\n")

    values = {}
    for key, prompt, default, _required, hint in QUESTIONS:
        out(f"\n{key}")
        values[key] = ask(prompt, existing.get(key) or default, required=False, hint=hint)

    if not values.get("SUPABASE_URL") or not values.get("SUPABASE_SERVICE_ROLE_KEY"):
        out("\n[提醒] Supabase 未填写完整：应用可以启动，但注册登录和数据存储不可用。")
        out("       建议参考 README「初始化 Supabase」一节，并在 SQL Editor 执行 docs/supabase_setup.sql")
    if not values.get("API_KEY"):
        out("[提醒] API_KEY 未填写：AI 生成/优化/测试对话功能不可用。")

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    lines = ["# 由引导脚本生成，可随时手动编辑本文件", ""]
    lines += [f"{key}={values.get(key, '')}" for key, *_ in QUESTIONS]
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    out(f"\n配置已写入 {ENV_FILE}")
    return values


def find_free_port(preferred):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", preferred))
            return preferred
        except OSError:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]


def wait_until_up(port, timeout=60):
    url = f"http://127.0.0.1:{port}/"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False


def launch():
    port = find_free_port(int(os.environ.get("PORT", "8000")))
    out(f"\n正在启动服务（端口 {port}）...")
    env = os.environ.copy()
    env["PORT"] = str(port)
    proc = subprocess.Popen([str(VENV_PYTHON), "run_server.py"], cwd=str(APP_DIR), env=env)
    if wait_until_up(port):
        url = f"http://127.0.0.1:{port}"
        out(f"\n✅ 启动成功：{url}")
        out("   关闭本窗口或按 Ctrl+C 即可停止服务")
        if "--no-browser" not in sys.argv and not os.environ.get("PROMPT_WORKSHOP_NO_BROWSER"):
            webbrowser.open(url)
        try:
            proc.wait()
        except KeyboardInterrupt:
            proc.terminate()
            out("\n服务已停止")
    else:
        out("服务启动超时，请查看上方日志排查。")


def main():
    ensure_console()
    if sys.version_info < (3, 9):
        die("需要 Python 3.9 及以上版本", "请到 https://www.python.org/downloads/ 安装后重试")
    if not APP_DIR.exists():
        die(f"未找到应用目录 {APP_DIR}", "请在仓库根目录下运行本脚本")
    out("=" * 46)
    out("  提示词工坊 (Prompt Workshop) 启动引导")
    out("=" * 46)
    ensure_venv()
    ensure_config()
    launch()


if __name__ == "__main__":
    main()
