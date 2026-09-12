#!/bin/bash
# 提示词工坊 - macOS 一键启动（双击运行）
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  echo "[提示] 未找到 Python 3，即将安装 Apple 命令行工具（约几分钟）。"
  echo "       安装完成后，请重新双击本文件。"
  xcode-select --install
  read -p "按回车键关闭..."
  exit 1
fi

exec python3 scripts/setup.py
