#!/bin/bash
# 重新生成 Tailwind 静态 CSS（修改模板/JS 中的类名后运行；部署环境无需 Node）
# 依赖: Node.js（npx）
set -e
cd "$(dirname "$0")/../prompt_generator"
npx -y tailwindcss@3.4.17 -c tailwind.config.js -i static/css/tailwind.src.css -o static/css/tailwind.css --minify
echo "已生成 static/css/tailwind.css"
