#!/usr/bin/env python3
"""macOS 版都市回响 — 网易云音乐浮动歌词。

用法：
  .venv/bin/python main_mac.py              # 检测网易云音乐 Mac 版并显示浮动歌词
  .venv/bin/python main_mac.py --local      # 本地播放模式（导入音乐+LRC歌词）
"""
import argparse
import logging
import os
import sys

# QAudioBufferOutput requires the FFmpeg backend.
os.environ["QT_MEDIA_BACKEND"] = "ffmpeg"

from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QMessageBox
from settings import SettingsStore, app_directory
from fonts import FontLibrary
from app_info import APP_NAME, APP_VERSION


def main():
    parser = argparse.ArgumentParser(description=f"{APP_NAME} · macOS 桌面音乐伴侣")
    parser.add_argument("--local", action="store_true",
                        help="本地播放模式（手动导入音乐和 LRC 歌词文件）")
    args = parser.parse_args()

    # ── 日志 ──
    state_dir = app_directory() / ".state"
    state_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=state_dir / "app.log", level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s", encoding="utf-8",
    )
    logging.info("Starting macOS app; pid=%s", os.getpid())

    # ── Qt 应用 ──
    app = QApplication(sys.argv[:1])
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("FloatingLyrics")
    app.setStyle("Fusion")
    app.setFont(QFont("PingFang SC", 10))
    app.setQuitOnLastWindowClosed(False)

    def exception_hook(error_type, error, traceback):
        logging.error("Unhandled exception", exc_info=(error_type, error, traceback))
        QMessageBox.critical(None, "运行出现问题",
                             f"{error}\n\n详细信息已保存到：{state_dir / 'app.log'}")
        app.exit(1)

    sys.excepthook = exception_hook

    # ── 设置 ──
    store = SettingsStore(state_dir / "settings.ini")
    prefs = store.load()

    # ── 导入 UI 组件（延迟，确保 QApplication 已创建）──
    from controls import ControlPanel, app_icon
    from overlay import LyricsOverlay

    app.setWindowIcon(app_icon(prefs.theme))

    # ── 播放器 ──
    if args.local:
        from player import MusicPlayer
        player = MusicPlayer()
        mode_name = "本地播放"
    else:
        from macos_netease import MacNeteasePlayer
        player = MacNeteasePlayer()
        mode_name = "网易云联动"

    logging.info("Mode: %s", mode_name)

    # ── 覆盖层 & 控制面板 ──
    overlay = LyricsOverlay(player, prefs)
    fonts = FontLibrary(state_dir / "fonts")
    panel = ControlPanel(player, overlay, prefs, store, font_library=fonts)

    # 连接歌词信号到 overlay
    player.document_changed.connect(overlay.set_document)

    # ── 歌词偏移：↑↓ 快捷键 + 每首歌自动记忆 ──
    if hasattr(player, 'set_offset_store'):
        from macos_netease import OffsetStore
        from PySide6.QtGui import QShortcut, QKeySequence
        from PySide6.QtCore import Qt

        offset_store = OffsetStore(state_dir / "offsets.json")
        player.set_offset_store(offset_store)

        OFFSET_STEP = 200  # 每次 ±200ms

        shortcut_up = QShortcut(QKeySequence(Qt.Key.Key_Up), panel)
        shortcut_up.setContext(Qt.ShortcutContext.ApplicationShortcut)
        shortcut_up.activated.connect(lambda: player.adjust_offset(OFFSET_STEP))

        shortcut_down = QShortcut(QKeySequence(Qt.Key.Key_Down), panel)
        shortcut_down.setContext(Qt.ShortcutContext.ApplicationShortcut)
        shortcut_down.activated.connect(lambda: player.adjust_offset(-OFFSET_STEP))

        logging.info("Lyric offset shortcuts enabled: ↑ +%dms, ↓ -%dms", OFFSET_STEP, OFFSET_STEP)

    app.aboutToQuit.connect(lambda: store.save(prefs))
    if hasattr(player, 'stop'):
        app.aboutToQuit.connect(player.stop)
    if hasattr(panel, 'tray') and panel.tray:
        app.aboutToQuit.connect(panel.tray.hide)

    panel.fit_to_screen(app.primaryScreen().availableGeometry())
    overlay.show()
    panel.show()

    logging.info("UI initialized; mode=%s", mode_name)

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
