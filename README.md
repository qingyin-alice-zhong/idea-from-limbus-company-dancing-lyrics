# 都市回响 · macOS 版 (Dancing Lyrics)

> 灵感来自 Limbus Company 的桌面歌词效果 —— macOS 适配版

Windows 版请切换到 [`main`](https://github.com/Celine258/idea-from-limbus-company-dancing-lyrics/tree/main) 分支。

##功能

- **网易云音乐同步** — 自动检测正在播放的歌曲，实时同步歌词
- **桌面悬浮歌词** — 透明无边框窗口，始终置顶显示
- **多种动画效果** — 波纹·波动、波纹·抖动、跌落·波动、跌落·抖动等
- **同步偏移** — ↑↓ 键微调 ±200ms，自动记忆每首歌的偏移值
- **控制面板** — 字体、颜色、动画、律动等全可调

## 📋 系统要求

| 项目 | 要求 |
|------|------|
| 系统 | macOS 12+ (Monterey 及以上) |
| Python | 3.10+ |
| 音乐播放器 | 网易云音乐 Mac 版 |
| 外部工具 | [`nowplaying-cli`](https://github.com/kirtan-shah/nowplaying-cli) (通过 Homebrew 安装) |

## 安装与运行

### 1. 安装 nowplaying-cli

```bash
brew install nowplaying-cli
```

### 2. 克隆仓库

```bash
git clone -b mac-version https://github.com/Celine258/idea-from-limbus-company-dancing-lyrics.git
cd idea-from-limbus-company-dancing-lyrics
```

### 3. 创建虚拟环境并安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. 运行

```bash
python main_mac.py
```

或使用便捷脚本：

```bash
chmod +x start.sh
./start.sh
```

## 使用说明

1. 打开**网易云音乐**并播放歌曲
2. 运行本程序，歌词会自动出现在桌面上
3. 点击系统托盘图标打开**控制面板**，调整外观和效果

### 快捷键

| 快捷键 | 功能 |
|--------|------|
| `↑` | 歌词提前 200ms |
| `↓` | 歌词延后 200ms |

偏移值会自动保存，下次播放同一首歌时自动恢复。新歌继承当前偏移（不归零）。

## 项目结构

```
├── main_mac.py          # macOS 入口
├── macos_netease.py     # 网易云音乐 macOS 适配（nowplaying-cli）
├── controls.py          # 控制面板 UI
├── overlay.py           # 桌面悬浮歌词窗口
├── settings.py          # 设置管理
├── themes.py            # 主题与样式
├── fonts.py             # 字体管理
├── requirements.txt     # Python 依赖
├── start.sh             # 启动脚本
├── 安装.sh              # 一键安装脚本
└── 卸载.sh              # 卸载脚本
```

## 已知限制

- 仅支持**网易云音乐 Mac 版**（依赖 macOS Now Playing 接口）
- 暂停/播放检测延迟约 500ms（轮询间隔）
- 需要安装 `nowplaying-cli`，不支持系统原生方式读取 Now Playing

## 版本

当前版本：**v0.6.0-beta.2**

## 致谢

- 创作者：Bilibili - 鈴仙優昙華院因幡
- 灵感来源：[Limbus Company](https://limbuscompany.com/)
- Now Playing 读取：[nowplaying-cli](https://github.com/kirtan-shah/nowplaying-cli)
