# Prompt Generator 项目上下文

我们在开发一个 Prompt Generator 项目，目前进展：

1. 项目结构：

project/
├── server.py          # FastAPI 主服务
├── static/           
│   ├── css/
│   │   └── style.css  # 黑色主题，左右布局
│   └── js/
│       └── main.js    # 处理提示词生成和测试
├── templates/
│   └── index.html     # 左右分栏布局
├── config/
│   └── prompts/
│       └── metaprompt.txt  # 提示词模板
└── docs/
    └── context_template.md # 本文件

2. 关键功能代码：

// main.js 中的变量处理
if (data.variables && data.variables.length > 0) {
    variableInputs.innerHTML = data.variables.map(variable => {
        return `
            <div class="form-group">
                <label for="var-${variable}">变量 ${variable}:</label>
                <input type="text" 
                       id="var-${variable}" 
                       name="${variable}"
                       placeholder="请输入 ${variable} 的值"
                       required>
            </div>
        `;
    }).join('');
}

3. 核心功能：
- 提示词生成：
  * 支持任务描述输入
  * 支持变量定义
  * 生成结构化提示词
- 提示词测试：
  * 变量值输入
  * 实时测试
  * 结果展示

4. 最近的改动：
- 修复了变量处理问题（移除了错误的 USER_ 前缀）
- 更新了 UI 为黑色主题和左右布局
- 讨论了部署方案（Vercel/本地服务器）

5. 待解决的问题：
[在这里添加你下次想讨论的问题]

注：使用此模板时，请更新"最近的改动"和"待解决的问题"部分，并提供相关的具体问题描述。
