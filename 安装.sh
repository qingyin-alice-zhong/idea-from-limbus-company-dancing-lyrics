#!/bin/bash
# ╔══════════════════════════════════════════════════════════════╗
# ║  都市回响 macOS 版 — 一键安装                                ║
# ║  灵感来自 Limbus Company 舞蹈歌词效果                        ║
# ╚══════════════════════════════════════════════════════════════╝
set -e
cd "$(dirname "$0")"
APP_DIR="$(pwd)"

echo ""
echo "  ╔═══════════════════════════════════════╗"
echo "  ║     都市回响 · macOS 版 · 安装器      ║"
echo "  ╚═══════════════════════════════════════╝"
echo ""

# ── 检查 Python ──
PYTHON=""
for candidate in python3.12 python3.11 python3.10 python3.13 python3; do
    p=$(which "$candidate" 2>/dev/null || true)
    if [ -n "$p" ]; then
        ver=$("$p" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || true)
        major=$(echo "$ver" | cut -d. -f1)
        minor=$(echo "$ver" | cut -d. -f2)
        if [ "$major" = "3" ] && [ "$minor" -ge 10 ] && [ "$minor" -le 13 ]; then
            PYTHON="$p"
            echo "  ✓ 找到 Python $ver ($p)"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo "  ✗ 未找到 Python 3.10-3.13"
    echo ""
    echo "  请先安装 Python："
    echo "    brew install python@3.12"
    echo ""
    echo "  安装完成后重新运行此脚本。"
    exit 1
fi

# ── 检查网易云音乐 ──
if [ -d "/Applications/NeteaseMusic.app" ]; then
    echo "  ✓ 已安装网易云音乐 Mac 版"
else
    echo "  ⚠ 未检测到网易云音乐 Mac 版"
    echo "    从 App Store 或 https://music.163.com/#/download 下载安装"
    echo "    安装后可正常使用本程序。"
fi

# ── 创建虚拟环境 ──
echo ""
if [ -d ".venv" ]; then
    echo "  → 虚拟环境已存在，检查依赖..."
else
    echo "  → 创建 Python 虚拟环境..."
    "$PYTHON" -m venv .venv
    echo "  ✓ 虚拟环境已创建"
fi

# ── 安装依赖 ──
echo "  → 安装/更新依赖 (PySide6, numpy, requests)..."
.venv/bin/pip install --upgrade pip -q 2>/dev/null
.venv/bin/pip install PySide6 numpy requests -q 2>/dev/null
echo "  ✓ 依赖安装完成"

# ── 验证导入 ──
echo "  → 验证模块..."
.venv/bin/python -c "
import sys; sys.path.insert(0, '.')
import settings, app_info, lrc, fonts, animation, overlay, macos_netease, controls
print('  ✓ 所有模块验证通过')
" 2>/dev/null || {
    echo "  ✗ 模块验证失败，请检查错误信息"
    exit 1
}

# ── 创建 .state 目录 ──
mkdir -p .state/fonts

# ── 设置启动脚本权限 ──
chmod +x start.sh 2>/dev/null || true

echo ""
echo "  ╔═══════════════════════════════════════╗"
echo "  ║           ✓ 安装完成！                ║"
echo "  ╚═══════════════════════════════════════╝"
echo ""
echo "  使用方法："
echo "    1. 打开网易云音乐 Mac 版，播放一首歌"
echo "    2. 双击 start.sh 或在终端运行："
echo "       cd $APP_DIR && ./start.sh"
echo "    3. 歌词将自动浮现在桌面上"
echo ""
echo "  首次启动时 macOS 可能询问辅助功能权限（用于检测播放状态）"
echo "  请在 系统设置 → 隐私与安全 → 辅助功能 中允许终端。"
echo ""
echo "  控制面板说明："
echo "    • 点击 '效果' 页签调整动画风格、字体、颜色"
echo "    • 系统托盘图标可快速显示/隐藏歌词"
echo "    • 右键托盘图标可退出程序"
echo ""
