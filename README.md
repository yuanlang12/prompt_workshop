# 提示词工坊 (Prompt Workshop)

一个开源的 AI 提示词管理与优化平台。以「项目」为单位管理你的提示词，支持 AI 生成/优化提示词、版本历史、变量提取，内置多模型测试对话（支持图片多模态输入与流式输出）。

## 功能特性

- **项目管理**：按项目组织提示词，支持创建、重命名、删除
- **提示词编辑**：保存提示词的 System / User 两部分内容，自动提取 `{{变量}}`
- **版本历史**：每次修改自动留档，可随时查看、回滚任意版本
- **AI 优化**：基于内置 Metaprompt 对提示词进行一键优化与修订
- **测试对话**：选择模型实时测试提示词效果，支持流式输出、多轮 User 消息、图片（多模态）输入
- **多模型支持**：任何 OpenAI 兼容接口均可接入（OpenAI / DeepSeek / Qwen / Ollama 等）
- **用户系统**：注册、登录、邮箱验证、重置密码（基于 Supabase Auth）

## 技术栈

- 后端：Python / FastAPI + Jinja2
- 前端：原生 HTML / CSS / JavaScript
- 数据与认证：Supabase（PostgreSQL + Auth）
- LLM：OpenAI 兼容 Chat Completions API

## 快速开始

### 前置要求

- Python 3.9+
- 一个 [Supabase](https://supabase.com) 免费项目（用于用户认证和数据存储）
- 一个 LLM API Key（任何 OpenAI 兼容服务均可）

### 方式一：一键启动（推荐）

克隆仓库后双击根目录的启动器，脚本会自动创建虚拟环境、安装依赖、交互式引导填入 Supabase 与 LLM 配置，完成后启动服务并自动打开浏览器：

- **macOS**：双击 `start_mac.command`（如被系统拦截：右键 →「打开」，或在终端执行 `bash start_mac.command`）
- **Windows**：双击 `start_windows.bat`

> 注意：Supabase 的建表操作仍需手动执行一次，见下方「初始化 Supabase」；之后再次双击启动器即可直接启动。

### 方式二：手动安装

#### 1. 安装依赖

```bash
git clone https://github.com/yuanlang12/prompt_workshop.git
cd prompt_workshop

python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

#### 2. 初始化 Supabase

1. 在 [Supabase](https://supabase.com) 创建一个免费项目
2. 打开 **SQL Editor**，执行 [`docs/supabase_setup.sql`](docs/supabase_setup.sql) 的全部内容（建表 + 索引 + RLS）
3. 在 **Project Settings -> API** 页面找到下面三个值，下一步会用到：
   - `Project URL`
   - `anon public` key
   - `service_role` key

> 提示：本地试用可在 **Authentication -> Providers -> Email** 中关闭 "Confirm email" 跳过邮箱验证；生产环境建议开启并配置自定义 SMTP。

#### 3. 配置环境变量

```bash
cp prompt_generator/config/.env.example prompt_generator/config/.env
# 编辑 prompt_generator/config/.env，填入你的配置
```

```dotenv
# LLM（任何 OpenAI 兼容接口）
API_URL=https://api.openai.com/v1/chat/completions
API_KEY=sk-xxxxxxxx
MODEL_NAME=gpt-4o-mini

# Supabase
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_KEY=your-anon-public-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

完整配置项见 [`prompt_generator/config/.env.example`](prompt_generator/config/.env.example)。

#### 4. 启动

```bash
python prompt_generator/run_server.py
```

看到启动提示后访问 `http://127.0.0.1:8000`（如端口被占用会自动换端口，以控制台输出为准）。

## 环境变量说明

| 变量 | 必填 | 说明 |
|---|---|---|
| `API_URL` | 是 | OpenAI 兼容 Chat Completions 接口地址 |
| `API_KEY` | 是 | LLM 服务 API Key |
| `MODEL_NAME` | 否 | 默认模型，默认 `gpt-4o-mini` |
| `AVAILABLE_MODELS` | 否 | 前端可选模型列表，格式 `model_id:显示名称`，逗号分隔 |
| `SUPABASE_URL` | 是 | Supabase 项目地址 |
| `SUPABASE_KEY` | 是 | Supabase anon public key |
| `SUPABASE_SERVICE_ROLE_KEY` | 是 | Supabase service_role key（仅后端使用，勿泄露） |
| `SECRET_KEY` | 否 | 旧版本地令牌签名密钥，不设则每次启动随机生成 |
| `PORT` | 否 | 服务端口，默认 `8000` |
| `LOG_LEVEL` | 否 | 日志级别，默认本地 `DEBUG`、Vercel 上 `INFO` |

### 常见 LLM 服务配置示例

| 服务 | API_URL | 说明 |
|---|---|---|
| OpenAI | `https://api.openai.com/v1/chat/completions` | 官方 |
| DeepSeek | `https://api.deepseek.com/v1/chat/completions` | 官方 |
| Ollama | `http://localhost:11434/v1/chat/completions` | 本地模型，Key 可留空占位 |
| 302.ai 等聚合服务 | 见对应文档 | 单一 Key 调用多家模型 |

## 部署

### Vercel（仓库已含 `vercel.json` 配置）

1. Fork / 导入本仓库到 Vercel
2. 在项目的 **Environment Variables** 中配置上表中的全部必填变量（Vercel 环境下无需 `.env` 文件）
3. 部署即可，入口为根目录 `app.py`

### 自有服务器

参考 [`deploy.sh`](deploy.sh)（Ubuntu + Nginx + systemd + uvicorn），按需修改域名与路径。

## 目录结构

```
├── app.py                    # Vercel 入口
├── requirements.txt
├── start_mac.command         # macOS 一键启动（双击）
├── start_windows.bat         # Windows 一键启动（双击）
├── scripts/setup.py          # 安装与启动引导脚本
├── prompt_generator/
│   ├── server.py             # FastAPI 主应用与 API 路由
│   ├── run_server.py         # 本地启动脚本
│   ├── auth.py / auth_routes.py / supabase_auth.py   # 认证
│   ├── supabase_db.py        # 数据访问层（Supabase）
│   ├── config/
│   │   ├── settings.py       # 环境变量加载
│   │   ├── .env.example      # 配置模板
│   │   └── prompts/          # 内置 Metaprompt 等提示词模板
│   ├── static/               # 前端静态资源
│   └── templates/            # 页面模板
├── docs/
│   ├── supabase_setup.sql    # Supabase 建表脚本
│   └── history/              # 历史开发记录
└── website/                  # 官网落地页
```

## 安全提示

- `config/.env` 已在 `.gitignore` 中，**切勿**将真实密钥提交到仓库或写进文档
- `SUPABASE_SERVICE_ROLE_KEY` 与 `API_KEY` 等同于你账户的完全控制权，仅保存在服务端环境变量中
- Supabase 数据表已启用 RLS 且未开放客户端直连策略，所有数据读写均由后端使用 service_role 密钥完成

## License

[MIT](LICENSE)
