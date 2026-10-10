"""Diagnostic: test overlay rendering pipeline directly."""
import sys, os, logging
os.environ["QT_MEDIA_BACKEND"] = "ffmpeg"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(message)s")

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv[:1])
app.setStyle("Fusion")
app.setFont(QFont("PingFang SC", 10))
app.setQuitOnLastWindowClosed(False)

from settings import SettingsStore, app_directory, Preferences
from overlay import LyricsOverlay
from macos_netease import MacNeteasePlayer

state_dir = app_directory() / ".state"
store = SettingsStore(state_dir / "settings.ini")
prefs = store.load()

player = MacNeteasePlayer()
overlay = LyricsOverlay(player, prefs)
player.document_changed.connect(overlay.set_document)

overlay.show()

def diag():
    print(f"--- DIAG ---")
    print(f"  player.playing={player.playing} player.ended={player.ended} player.connected={player.connected}")
    print(f"  player.title='{player.title}' player.artist='{player.artist}'")
    print(f"  player.position()={player.position()} player.duration={player.duration}")
    print(f"  overlay.isVisible()={overlay.isVisible()}")
    print(f"  overlay.timeline={overlay.timeline}")
    print(f"  overlay.document={'has ' + str(len(overlay.document.lines)) + ' lines' if overlay.document else None}")
    print(f"  overlay.display_document={overlay.display_document is not None}")
    print(f"  overlay.timer.isActive()={overlay.timer.isActive()}")
    print(f"  overlay.geometry()={overlay.geometry()}")
    print(f"  overlay.size()={overlay.size()}")
    if overlay.timeline:
        pos = player.position()
        active = overlay.timeline.visible(pos, player.duration)
        print(f"  timeline.visible(pos={pos}, dur={player.duration}) -> {len(active)} items")
        for item in active[:3]:
            print(f"    [{item.index}] '{item.text[:30]}' start={item.start_ms} end={item.end_ms} opacity={item.opacity:.2f}")
    print(f"  overlay.layouts count={len(overlay.layouts)}")
    print()

timer = QTimer()
timer.setInterval(2000)
timer.timeout.connect(diag)
timer.start()

# Also run once after 3 seconds
QTimer.singleShot(3000, diag)

print("Diagnostic running. Press Ctrl+C to stop.")
app.exec()
