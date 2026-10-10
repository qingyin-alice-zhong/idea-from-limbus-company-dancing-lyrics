# 都市回响 macOS 版

灵感来自 Limbus Company 的舞蹈歌词效果。基于 [原项目](https://github.com/Celine258/idea-from-limbus-company-dancing-lyrics) 移植。

## 安装

1. **需要 Python 3.10–3.13**。如未安装：`brew install python@3.12`
2. 在终端运行安装脚本：
   ```
   cd dancing-lyrics-mac
   bash 安装.sh
   ```
   自动创建虚拟环境并安装依赖。无需手动 pip。

## 使用

1. 打开 **网易云音乐 Mac 版**，播放一首歌。
2. 双击 `start.sh` 或在终端运行：
   ```
   ./start.sh
   ```
3. 歌词将自动浮现在桌面上。点击托盘图标或控制面板调整效果。

> 首次启动时 macOS 可能询问辅助功能权限，请在 **系统设置 → 隐私与安全 → 辅助功能** 中允许终端。

## 更新

新版覆盖原目录，再次运行 `bash 安装.sh`。`.state/` 下的个人设置、字体、预设会保留。

## 卸载

```
bash 卸载.sh
```

保留个人设置。如需完全删除，手动删除整个目录。

## 注意事项

- **⚠️ 版本**：需要 macOS 上的 **网易云音乐 Mac 版**（从 App Store 或官网下载）。
- **音频能量**：macOS 版使用模拟波浪（非真实音频采样），歌词弹跳为节拍模拟。
- **VIP 歌曲**：部分 VIP 歌曲搜索 API 可能返回翻唱版歌词。实际通过网易云播放时，程序优先使用 App 内歌曲 ID 直接获取原版歌词。
- **本地模式**：`./start.sh --local` 可手动导入本地音乐 + LRC 歌词文件。

## 与 Windows 版对照

| | Windows 版 | macOS 版 |
|---|---|---|
| 安装 | 解压 ZIP + 双击 `安装网易云联动.bat` | `bash 安装.sh` |
| 启动 | 网易云播放栏点击"都市回响" | `./start.sh` |
| 歌曲检测 | BetterNCM 插件注入 | AppleScript 轮询 |
| 歌词来源 | 内部 Redux store hook | 网易云公开 API |
| 音频能量 | WASAPI 进程音频采集 | 模拟波浪 |
| 卸载 | 双击 `卸载网易云联动.bat` | `bash 卸载.sh` |
| 网易云版本 | 3.1.40 / 3.1.41 x64 | Mac 版（无版本限制） |

## 致谢

原项目：[Celine258](https://github.com/Celine258/idea-from-limbus-company-dancing-lyrics) · 创作者：Bilibili-鈴仙優昙華院因幡 · FACE THE SIN. SAVE THE E.G.O
