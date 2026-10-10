"""Quick test: does MacNeteasePlayer detect the song?"""
import sys, time
sys.path.insert(0, '.')
from macos_netease import _query_nowplaying, _NOWPLAYING_CLI, MacNeteasePlayer

print(f"nowplaying-cli path: {_NOWPLAYING_CLI}")
print()

info = _query_nowplaying()
print(f"=== Direct query ===")
if info:
    print(f"  State: {info.state}")
    print(f"  Title: {info.title}")
    print(f"  Artist: {info.artist}")
    print(f"  Duration: {info.duration_ms}ms")
    print(f"  Position: {info.position_ms}ms")
else:
    print("  FAILED - no info returned")
