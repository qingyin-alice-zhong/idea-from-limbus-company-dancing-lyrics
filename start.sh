#!/bin/bash
# 都市回响 macOS 版 — 启动
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
    echo ""
    echo "  ✗ 尚未安装。请先运行："
    echo "    bash 安装.sh"
    echo ""
    exit 1
fi

echo "  🎵 都市回响 启动中..."
echo "     打开网易云音乐 Mac 版并播放歌曲，歌词将自动浮现。"
echo "     按 Ctrl+C 或右键托盘图标退出。"
echo ""

.venv/bin/python main_mac.py "$@"
