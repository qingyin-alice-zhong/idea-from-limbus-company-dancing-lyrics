#!/bin/bash
# ╔══════════════════════════════════════════════════════════════╗
# ║  都市回响 macOS 版 — 卸载                                    ║
# ╚══════════════════════════════════════════════════════════════╝
cd "$(dirname "$0")"

echo ""
echo "  ╔═══════════════════════════════════════╗"
echo "  ║     都市回响 · macOS 版 · 卸载        ║"
echo "  ╚═══════════════════════════════════════╝"
echo ""

# ── 确认 ──
read -p "  确认卸载？个人设置(.state)将保留。[y/N] " confirm
if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    echo "  已取消。"
    exit 0
fi

# ── 删除虚拟环境 ──
if [ -d ".venv" ]; then
    rm -rf .venv
    echo "  ✓ 已删除虚拟环境 (.venv)"
else
    echo "  - 虚拟环境不存在，跳过"
fi

# ── 删除 Python 缓存 ──
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
echo "  ✓ 已清理 Python 缓存"

echo ""
echo "  ╔═══════════════════════════════════════╗"
echo "  ║           ✓ 卸载完成                  ║"
echo "  ╚═══════════════════════════════════════╝"
echo ""
echo "  已保留："
echo "    • .state/ — 个人设置、导入的字体和预设"
echo "    • 源码文件 — 重新运行 安装.sh 即可恢复"
echo ""
echo "  如需完全删除，手动删除整个目录："
echo "    rm -rf $(pwd)"
echo ""
