"""macOS 网易云音乐联动：通过 AppleScript 检测当前播放 + 网易云公开 API 获取歌词。

适用于 macOS 上的网易云音乐客户端（NeteaseMusic.app）。
不需要注入任何 DLL 或插件——纯 API 方式。
"""
import json
import logging
import re
import subprocess
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path

import requests
from PySide6.QtCore import QObject, QTimer, Signal

from lrc import LyricLine, LyricDocument, TimedWord

logger = logging.getLogger(__name__)


class OffsetStore:
    """每首歌的歌词偏移存储。只保存非零偏移，轻量级 JSON。"""
    def __init__(self, path: Path):
        self._path = path
        self._data: dict[str, int] = {}
        self._load()

    def _load(self):
        try:
            if self._path.exists():
                self._data = json.loads(self._path.read_text(encoding='utf-8'))
        except Exception:
            self._data = {}

    def _save(self):
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(json.dumps(self._data, ensure_ascii=False, indent=1), encoding='utf-8')
        except Exception as e:
            logger.debug('Failed to save offsets: %s', e)

    @staticmethod
    def _key(title: str, artist: str) -> str:
        return f"{title}|{artist}"

    def get(self, title: str, artist: str) -> int:
        return self._data.get(self._key(title, artist), 0)

    def set(self, title: str, artist: str, offset_ms: int):
        key = self._key(title, artist)
        if offset_ms == 0:
            self._data.pop(key, None)
        else:
            self._data[key] = offset_ms
        self._save()

# ─── AppleScript 模板 ───────────────────────────────────────────────

@dataclass
class NowPlaying:
    state: str        # "playing" | "paused" | "stopped"
    title: str
    artist: str
    duration_ms: int
    position_ms: int
    song_id: str


def _find_nowplaying_cli() -> str | None:
    """查找 nowplaying-cli 可执行文件路径。优先用系统安装的（更可靠）。"""
    import os, sys

    def _works(path: str) -> bool:
        """验证二进制确实能返回有效数据（非 null）。"""
        try:
            r = subprocess.run([path, "get", "playbackRate"], capture_output=True, text=True, timeout=2)
            return r.returncode == 0 and r.stdout.strip() not in ("", "null")
        except Exception:
            return False

    # 1. Homebrew / 系统路径（最可靠）
    for path in ["/opt/homebrew/bin/nowplaying-cli", "/usr/local/bin/nowplaying-cli"]:
        if os.path.isfile(path):
            return path
    # 2. PATH 搜索
    try:
        r = subprocess.run(["which", "nowplaying-cli"], capture_output=True, text=True, timeout=2)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except Exception:
        pass
    # 3. PyInstaller 打包内的 assets/nowplaying-cli（验证可用性）
    if getattr(sys, '_MEIPASS', None):
        bundled = os.path.join(sys._MEIPASS, "assets", "nowplaying-cli")
        if os.path.isfile(bundled) and _works(bundled):
            return bundled
    # 4. 开发模式下 assets/nowplaying-cli（验证可用性）
    dev_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "nowplaying-cli")
    if os.path.isfile(dev_path) and _works(dev_path):
        return dev_path
    return None


_NOWPLAYING_CLI = _find_nowplaying_cli()


def _query_nowplaying() -> NowPlaying | None:
    """通过 nowplaying-cli get-raw 读取 macOS Now Playing 信息（JSON 格式）。

    注意：nowplaying-cli 的 `get` 子命令对部分字段（如 elapsedTime）存在
    映射 bug，返回 0 而非真实值。改用 `get-raw` 获取完整 JSON 可靠数据。
    """
    if not _NOWPLAYING_CLI:
        return None
    try:
        result = subprocess.run(
            [_NOWPLAYING_CLI, "get-raw"],
            capture_output=True, text=True, timeout=2,
        )
        if result.returncode != 0:
            return None
        data = json.loads(result.stdout)

        title = data.get("kMRMediaRemoteNowPlayingInfoTitle", "") or ""
        artist = data.get("kMRMediaRemoteNowPlayingInfoArtist", "") or ""
        dur_s = float(data.get("kMRMediaRemoteNowPlayingInfoDuration", 0) or 0)
        elapsed_s = float(data.get("kMRMediaRemoteNowPlayingInfoElapsedTime", 0) or 0)
        rate = float(data.get("kMRMediaRemoteNowPlayingInfoPlaybackRate", 0) or 0)

        if not title:
            return None

        # playbackRate 可靠：播放时=1，暂停时=0
        state = "playing" if rate > 0 else "paused"
        return NowPlaying(
            state=state,
            title=title,
            artist=artist,
            duration_ms=int(dur_s * 1000),
            position_ms=int(elapsed_s * 1000),
            song_id="",
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError, json.JSONDecodeError) as e:
        logger.debug("nowplaying-cli query failed: %s", e)
        return None


# ─── 网易云公开 API 歌词获取 ─────────────────────────────────────────

_NETEASE_SEARCH_API = "https://music.163.com/api/search/get"
_NETEASE_LYRIC_API = "https://music.163.com/api/song/lyric"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://music.163.com/",
}
_SESSION = requests.Session()
_SESSION.headers.update(_HEADERS)


def search_song(title: str, artist: str = "") -> str | None:
    """通过关键词搜索歌曲，返回有歌词的最佳匹配 song_id。

    尝试多个候选，直到找到一个有歌词的。
    """
    query = f"{title} {artist}".strip()
    if not query:
        return None
    try:
        resp = _SESSION.post(
            _NETEASE_SEARCH_API,
            data={"s": query, "type": 1, "limit": 15, "offset": 0},
            timeout=5,
        )
        data = resp.json()
        songs = data.get("result", {}).get("songs", [])
        if not songs:
            return None

        artist_lower = artist.strip().lower()

        # 排序候选：标题+艺人匹配 > 标题匹配 > 其他
        def score(song):
            name_match = song.get("name", "").strip() == title.strip()
            song_artists = [a.get("name", "").lower() for a in song.get("artists", [])]
            artist_match = artist_lower and any(artist_lower in a for a in song_artists)
            return (name_match and artist_match, name_match, artist_match)

        candidates = sorted(songs, key=score, reverse=True)

        # 返回第一个有歌词的候选
        for song in candidates[:5]:
            sid = str(song["id"])
            if _has_lyrics(sid):
                return sid

        # 全部无歌词，返回得分最高的
        return str(candidates[0]["id"])
    except Exception as e:
        logger.warning("Search API failed: %s", e)
        return None


def _has_lyrics(song_id: str) -> bool:
    """快速检查歌曲是否有歌词。"""
    try:
        resp = _SESSION.get(
            _NETEASE_LYRIC_API,
            params={"id": song_id, "lv": 1},
            timeout=3,
        )
        data = resp.json()
        lrc = data.get("lrc", {}).get("lyric", "")
        return bool(lrc and len(lrc) > 20)
    except Exception:
        return False


def fetch_lyrics(song_id: str) -> LyricDocument | None:
    """通过歌曲 ID 获取歌词（LRC + 逐字 YRC + 翻译）。"""
    if not song_id:
        return None
    try:
        resp = _SESSION.get(
            _NETEASE_LYRIC_API,
            params={"id": song_id, "lv": 1, "kv": 1, "tv": -1, "yv": 1},
            timeout=5,
        )
        data = resp.json()
    except Exception as e:
        logger.warning("Lyric API failed: %s", e)
        return None

    # 优先使用 YRC（逐字时间），其次 LRC
    yrc_raw = data.get("yrc", {}).get("lyric", "")
    lrc_raw = data.get("lrc", {}).get("lyric", "")
    trans_raw = data.get("tlyric", {}).get("lyric", "")

    if not lrc_raw and not yrc_raw:
        return None

    # 解析 LRC
    lines = _parse_lrc_text(lrc_raw)

    # 解析 YRC 逐字时间并附加到 lines
    if yrc_raw:
        _attach_yrc(lines, yrc_raw)

    # 解析翻译
    if trans_raw:
        _attach_translations(lines, trans_raw)

    if not lines:
        return None

    return LyricDocument(lines=lines, warnings=[], offset_ms=0)


def _parse_lrc_text(lrc_text: str) -> list[LyricLine]:
    """解析标准 LRC 格式文本。"""
    lines = []
    pattern = re.compile(r"\[(\d+):(\d+)[.:](\d+)\]\s*(.+)")
    for raw_line in lrc_text.split("\n"):
        raw_line = raw_line.strip()
        m = pattern.match(raw_line)
        if not m:
            continue
        minutes, seconds, frac, text = m.groups()
        # 处理不同精度的毫秒：2位(.xx) vs 3位(.xxx)
        if len(frac) == 2:
            frac = frac + "0"
        elif len(frac) == 1:
            frac = frac + "00"
        ms = int(minutes) * 60000 + int(seconds) * 1000 + int(frac[:3])
        text = text.strip()
        if text and not _is_metadata(text):
            lines.append(LyricLine(start_ms=ms, text=text, words=[], translation=""))
    lines.sort(key=lambda l: l.start_ms)
    return lines


def _is_metadata(text: str) -> bool:
    """检查是否为 LRC 元数据行（跳过 作词/作曲/编曲 等制作信息）。"""
    lower = text.strip().lower()
    # 标准 LRC 元数据标签
    if any(lower.startswith(prefix) for prefix in ("ar:", "ti:", "al:", "by:", "offset:")):
        return True
    # 中文制作信息
    if any(kw in lower for kw in ("作词", "作曲", "编曲", "制作人", "录音", "混音", "母带", "吉他", "贝斯", "鼓", "钢琴", "和声", "出品", "发行", "OP:", "SP:")):
        return True
    return False


def _attach_yrc(lines: list[LyricLine], yrc_text: str):
    """解析 YRC 逐字时间格式并附加到对应歌词行。

    YRC 格式示例: [1234,5678]text(startMs,durationMs,0)word1(startMs,durationMs,0)word2
    """
    yrc_pattern = re.compile(r"\[(\d+),(\d+)\](.+)")
    word_pattern = re.compile(r"(.*?)\((\d+),(\d+),\d+\)")

    yrc_lines = {}
    for raw_line in yrc_text.split("\n"):
        raw_line = raw_line.strip()
        m = yrc_pattern.match(raw_line)
        if not m:
            continue
        line_start = int(m.group(1))
        content = m.group(3)
        words = []
        for wm in word_pattern.finditer(content):
            word_text = wm.group(1)
            word_start = int(wm.group(2))
            word_dur = int(wm.group(3))
            if word_text.strip():
                words.append((word_start, word_start + word_dur, word_text))
        if words:
            yrc_lines[line_start] = words

    # 将 YRC 逐字时间匹配到 LRC 行（±500ms 容差）
    for line in lines:
        best_key = None
        best_dist = 501
        for key in yrc_lines:
            dist = abs(key - line.start_ms)
            if dist < best_dist:
                best_dist = dist
                best_key = key
        if best_key is not None and best_dist <= 500:
            word_data = yrc_lines[best_key]
            timed_words = []
            text_pos = 0
            for ws, we, wt in word_data:
                idx = line.text.find(wt, text_pos)
                if idx >= 0:
                    timed_words.append(TimedWord(
                        start_ms=ws, end_ms=we,
                        text_start=idx, text_end=idx + len(wt),
                    ))
                    text_pos = idx + len(wt)
            if timed_words:
                object.__setattr__(line, 'words', timed_words)


def _attach_translations(lines: list[LyricLine], trans_text: str):
    """将翻译行匹配到对应歌词行。"""
    trans_pattern = re.compile(r"\[(\d+):(\d+)\.(\d+)\](.+)")
    trans_map = {}
    for raw_line in trans_text.split("\n"):
        raw_line = raw_line.strip()
        m = trans_pattern.match(raw_line)
        if not m:
            continue
        minutes, seconds, frac, text = m.groups()
        if len(frac) == 2:
            frac += "0"
        elif len(frac) == 1:
            frac += "00"
        ms = int(minutes) * 60000 + int(seconds) * 1000 + int(frac[:3])
        text = text.strip()
        if text:
            trans_map[ms] = text

    for line in lines:
        best_key = None
        best_dist = 501
        for key in trans_map:
            dist = abs(key - line.start_ms)
            if dist < best_dist:
                best_dist = dist
                best_key = key
        if best_key is not None and best_dist <= 500:
            object.__setattr__(line, 'translation', trans_map[best_key])


# ─── macOS 网易云播放器适配 ──────────────────────────────────────────

class MacNeteasePlayer(QObject):
    """通过 AppleScript 轮询网易云音乐 Mac 版的播放状态。

    提供与 MusicPlayer 兼容的接口给 overlay 使用。
    """
    changed = Signal()
    discontinuity = Signal()
    document_changed = Signal(object)
    error = Signal(str)

    is_external = True  # 告诉 ControlPanel 切换到网易云联动模式

    def __init__(self, parent=None):
        super().__init__(parent)
        self.playing = False
        self.ended = False
        self.connected = False
        self.enabled = True
        self.duration = 0
        self.song_id = ""
        self.title = ""
        self.artist = ""
        self.status = "等待网易云音乐启动"

        # Position interpolation (same approach as original NeteasePlayer)
        self._anchor_ms = 0
        self._anchor_at = 0.0
        self._user_offset_ms = 0   # 每首歌的用户偏移（↑↓ 调整）
        self._offset_store: OffsetStore | None = None

        # Energy smoothing
        self._energy_samples: deque = deque(maxlen=64)
        self._energy_anchor = 0.0
        self._energy_at = 0.0

        # Lyrics cache
        self._lyrics_cache: dict[str, LyricDocument | None] = {}
        self.lyrics_received = False  # ControlPanel 检查此属性

        # Poll timer: 500ms interval (good balance of responsiveness vs overhead)
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(500)
        self._poll_timer.timeout.connect(self._poll)
        self._poll_timer.start()

        # State for detecting changes
        self._last_state = ""
        self._last_elapsed_ms = -1  # 用于通过 elapsedTime 变化检测播放
        self._stale_count = 0          # 连续未变化的轮询次数
        self._STALE_THRESHOLD = 1      # 1×200ms 不变即判定暂停

    def _poll(self):
        """轮询网易云音乐状态。"""
        info = _query_nowplaying()
        if info is None:
            if self.connected:
                self.connected = False
                self.playing = False
                self.ended = True
                self.status = "网易云音乐未运行"
                self.changed.emit()
            return

        self.connected = True
        self.status = "已连接网易云音乐"
        was_playing = self.playing
        old_id = self.song_id

        # playbackRate 可靠：播放时=1，暂停时=0。直接用它判断状态。
        now_playing = (info.state == "playing")
        self.ended = False
        self.duration = info.duration_ms
        self.title = info.title
        self.artist = info.artist

        if now_playing:
            # 正在播放：用快照位置作为 anchor，单调时钟插值填充中间帧
            if not self.playing or info.position_ms != self._last_elapsed_ms:
                self._anchor_ms = info.position_ms
                self._anchor_at = time.monotonic()
            self.playing = True
        else:
            # 暂停：锁定在当前快照位置
            self._anchor_ms = info.position_ms
            self._anchor_at = time.monotonic()
            self.playing = False
        self._last_elapsed_ms = info.position_ms

        # 检测歌曲切换
        new_id = info.song_id if info.song_id else f"{info.title}|{info.artist}"
        if new_id != old_id:
            self.song_id = new_id
            self.status = f"正在播放: {info.title}"
            # 切歌时重置 anchor 到新歌位置
            self._anchor_ms = info.position_ms
            self._anchor_at = time.monotonic()
            # 加载该歌曲保存的偏移；如果从未调过，继承当前偏移（不归零）
            if self._offset_store:
                saved = self._offset_store.get(info.title, info.artist)
                if saved != 0:
                    self._user_offset_ms = saved  # 有保存的，用保存的
                # else: 保持当前 _user_offset_ms 不变（继承上一首的偏移）
            self.discontinuity.emit()
            self.changed.emit()  # 通知控制面板刷新歌曲信息
            self._fetch_lyrics(info)
        # 播放状态变化
        elif self.playing != was_playing:
            self.changed.emit()

    def _fetch_lyrics(self, info: NowPlaying):
        """获取歌词（带缓存）。"""
        cache_key = self.song_id
        if cache_key in self._lyrics_cache:
            self.document_changed.emit(self._lyrics_cache[cache_key])
            return

        # 先尝试用 song_id 直接获取
        doc = None
        if info.song_id and info.song_id.isdigit():
            doc = fetch_lyrics(info.song_id)

        # 如果直接获取失败，搜索后再获取
        if doc is None and info.title:
            found_id = search_song(info.title, info.artist)
            if found_id:
                doc = fetch_lyrics(found_id)

        self._lyrics_cache[cache_key] = doc
        self.lyrics_received = (doc is not None)
        logger.info("Lyrics for '%s' by '%s': %s",
                    info.title, info.artist,
                    f"{len(doc.lines)} lines" if doc else "not found")
        self.document_changed.emit(doc)

    def set_offset_store(self, store: OffsetStore):
        """设置偏移存储（由 main_mac.py 初始化后注入）。"""
        self._offset_store = store

    def adjust_offset(self, delta_ms: int):
        """实时调整当前歌曲的歌词偏移。正值=歌词提前，负值=歌词延后。"""
        self._user_offset_ms += delta_ms
        if self._offset_store and self.title:
            self._offset_store.set(self.title, self.artist, self._user_offset_ms)
        self.changed.emit()
        logger.info('Lyric offset: %+dms for \'%s\'', self._user_offset_ms, self.title)

    @property
    def user_offset_ms(self) -> int:
        return self._user_offset_ms


    def position(self) -> int:
        """返回当前播放位置（毫秒），通过单调时钟插值 + 用户偏移。"""
        if not self.playing:
            return max(0, self._anchor_ms + self._user_offset_ms)
        elapsed = time.monotonic() - self._anchor_at
        pos = self._anchor_ms + int(elapsed * 1000) + self._user_offset_ms
        if self.duration > 0:
            pos = min(pos, self.duration)
        return max(0, pos)

    def energy_at(self, position_ms: int = 0) -> float:
        """返回音频能量值。macOS 上使用模拟波浪（无进程音频捕获）。"""
        # 用正弦波模拟节奏感的能量变化
        t = time.monotonic()
        import math
        # 多频叠加模拟音乐节拍感
        e = (0.35 + 0.25 * math.sin(t * 2.1)
             + 0.15 * math.sin(t * 3.7 + 1.2)
             + 0.10 * math.sin(t * 7.3 + 0.5))
        return max(0.0, min(1.0, e))

    def stop(self):
        self._poll_timer.stop()

    # Stubs for ControlPanel compatibility
    @property
    def media(self):
        return self

    def toggle(self):
        """通过 nowplaying-cli 切换播放/暂停。"""
        if _NOWPLAYING_CLI:
            try:
                subprocess.run([_NOWPLAYING_CLI, "togglePlayPause"],
                               capture_output=True, timeout=2)
            except Exception:
                pass

    def seek(self, ms: int):
        """通过 AppleScript 跳转。"""
        try:
            seconds = ms / 1000.0
            subprocess.run(
                ["osascript", "-e", f'tell application "NeteaseMusic" to set player position to {seconds}'],
                timeout=2, capture_output=True,
            )
            self._anchor_ms = ms
            self._anchor_at = time.monotonic()
            self.discontinuity.emit()
        except Exception:
            pass

    def set_volume(self, value: float):
        """通过 AppleScript 设置音量。"""
        try:
            subprocess.run(
                ["osascript", "-e", f'tell application "NeteaseMusic" to set sound volume to {value}'],
                timeout=2, capture_output=True,
            )
        except Exception:
            pass

    @property
    def has_audio_data(self):
        return True

    @has_audio_data.setter
    def has_audio_data(self, _):
        pass

    @property
    def analysis_error(self):
        return ""

    @analysis_error.setter
    def analysis_error(self, _):
        pass
