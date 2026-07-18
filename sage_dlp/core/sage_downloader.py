import gc
import os
import re
import shlex  # For safely parsing command arguments
import shutil
import signal
import subprocess  # For direct CLI command execution
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional, List, Set

from PySide6.QtCore import QObject, QThread, Signal

from .sage_yt_dlp import get_yt_dlp_path
from ..utils.sage_constants import (
    SUBPROCESS_CREATIONFLAGS,
    VIDEO_EXTENSIONS,
    AUDIO_EXTENSIONS,
    SUBTITLE_EXTENSIONS,
    MEDIA_EXTENSIONS,
)
from ..utils.sage_localization import LocalizationManager
from ..utils.sage_logger import logger

# Shorthand for localization
_ = LocalizationManager.get_text


# @lat: [[Core#sage_downloader]]
class SignalManager(QObject):
    update_formats = Signal(list)
    update_status = Signal(str)
    update_progress = Signal(float)
    playlist_info_label_visible = Signal(bool)
    playlist_info_label_text = Signal(str)
    selected_subs_label_text = Signal(str)
    playlist_select_btn_visible = Signal(bool)
    playlist_select_btn_text = Signal(str)
    llm_complete = Signal(str)  # emitted when LLM segmentation finishes: path to .srt


class DownloadThread(QThread):
    progress_signal = Signal(float)
    status_signal = Signal(str)
    finished_signal = Signal()
    error_signal = Signal(str)
    file_exists_signal = Signal(str)  # New signal for file existence
    update_details = Signal(str)  # New signal for filename, speed, ETA

    def __init__(
        self,
        url,
        path,
        format_id,
        is_audio_only=False,
        format_has_audio=False,
        subtitle_langs=None,
        is_playlist=False,
        merge_subs=False,
        resolution="",
        playlist_items=None,
        save_description=False,
        embed_chapters=False,
        cookie_file=None,
        browser_cookies=None,
        rate_limit=None,
        download_section=None,
        force_keyframes=False,
        proxy_url=None,
        geo_proxy_url=None,
        force_output_format=False,
        preferred_output_format="mp4",
        force_audio_format=False,
        preferred_audio_format="best",
        audio_normalization=False,
        filename_format=None,
        concurrent_fragments=1,
        subtitle_only_mode=False,
    ) -> None:
        super().__init__()
        self.url = url
        self.path = Path(path)
        self.format_id = format_id
        self.is_audio_only = is_audio_only
        self.format_has_audio = format_has_audio
        self.subtitle_langs = subtitle_langs if subtitle_langs else []
        self.is_playlist = is_playlist
        self.merge_subs = merge_subs
        self.resolution = resolution
        self.playlist_items = playlist_items
        self.save_description = save_description
        self.embed_chapters = embed_chapters
        self.cookie_file = cookie_file
        self.browser_cookies = browser_cookies
        self.rate_limit = rate_limit
        self.download_section = download_section
        self.force_keyframes = force_keyframes
        self.proxy_url = proxy_url
        self.geo_proxy_url = geo_proxy_url
        self.force_output_format = force_output_format
        self.preferred_output_format = preferred_output_format
        self.force_audio_format = force_audio_format
        self.preferred_audio_format = preferred_audio_format
        self.audio_normalization = audio_normalization
        self.filename_format = filename_format
        self.concurrent_fragments = concurrent_fragments
        # 仅字幕模式：跳过视频/音频下载，强制下载 json3 字幕并执行断句
        self.subtitle_only_mode: bool = bool(subtitle_only_mode)
        # LLM segmentation
        self.llm_segment_enabled: bool = False
        self.llm_config: dict = {}
        self.paused: bool = False
        self.cancelled: bool = False
        self.process: Optional[subprocess.Popen] = None
        self.current_filename: Optional[str] = None  # Initialize filename storage
        self.last_file_path: Optional[str] = None  # Initialize full file path storage
        self.subtitle_files: List[str] = []  # Track subtitle files that are created
        self.initial_subtitle_files: Set[Path] = set()  # Track initial subtitle files before download
        # 字幕临时目录：每次下载独立创建，用于隔离 json3 文件，
        # 避免共享下载目录下误抓到其他视频的 json3。
        # 断句生成的 SRT 仍会输出到 self.path（用户下载目录），完成后清理此目录。
        self.subtitle_temp_dir: Path = Path(tempfile.mkdtemp(prefix="sage_subs_"))
        logger.info(f"[Download] subtitle temp dir created: {self.subtitle_temp_dir}")

    def cleanup_partial_files(self) -> None:
        """Delete any partial files including .part and unmerged format-specific files"""
        try:
            pattern = re.compile(r"\.f\d+\.")  # Pattern to match format codes like .f243.
            for file_path in self.path.iterdir():
                if file_path.suffix == ".part" or pattern.search(file_path.name):
                    self._safe_delete_with_retry(file_path)
        except Exception as e:
            logger.exception(f"Error cleaning partial files: {e}")
            # Don't emit error signal for cleanup issues to avoid crashing the thread
            logger.error(f"Error cleaning partial files: {e}")

    def _safe_delete_with_retry(self, file_path: Path, max_retries: int = 5, delay: float = 2.0) -> None:
        """Safely delete a file with retry mechanism for file locking issues across platforms"""
        for attempt in range(max_retries):
            try:
                # Force garbage collection to release any Python-held file handles
                gc.collect()
                
                if file_path.exists():
                    file_path.unlink(missing_ok=True)
                    logger.info(f"Successfully deleted {file_path.name}")
                return
            except PermissionError as e:
                if attempt < max_retries - 1:
                    logger.warning(f"File {file_path.name} is locked, retrying in {delay} seconds... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    delay = min(delay * 1.5, 5.0)  # Exponential backoff, capped at 5 seconds
                else:
                    logger.error(f"Failed to delete {file_path.name} after {max_retries} attempts: {e}")
                    return
            except Exception as e:
                logger.error(f"Error deleting {file_path.name}: {e}")
                return

    def _terminate_process_tree(self, process: subprocess.Popen) -> None:
        """Terminate a process and all its children across platforms"""
        pid = process.pid
        
        try:
            if sys.platform == "win32":
                # Windows: Use taskkill to kill the entire process tree
                # /T = kill child processes, /F = force kill
                # Use subprocess.run with no encoding to avoid codec issues
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=SUBPROCESS_CREATIONFLAGS,
                )
                logger.debug(f"Killed process tree on Windows (PID: {pid})")
            else:
                # Unix-like systems: Kill the process group
                try:
                    # Try to kill the process group
                    os.killpg(os.getpgid(pid), signal.SIGTERM)
                    time.sleep(0.5)
                    # Force kill if still running
                    os.killpg(os.getpgid(pid), signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    # Process already terminated or no permission
                    pass
                logger.debug(f"Killed process group on Unix (PID: {pid})")
        except Exception as e:
            logger.warning(f"Error killing process tree: {e}")
            # Fallback to standard termination
            try:
                process.terminate()
                process.wait(timeout=2)
            except Exception:
                try:
                    process.kill()
                    process.wait()
                except Exception:
                    pass
        
        # Ensure process is waited on to avoid zombies
        try:
            process.wait(timeout=3)
        except Exception:
            pass

    def cleanup_subtitle_files(self) -> None:
        """Delete subtitle files after they have been merged into the video file"""
        deleted_count: List[int] = [0, 0]

        def safe_delete(path: Path) -> bool:
            try:
                # Check if file exists before trying to delete
                if path.exists():
                    path.unlink(missing_ok=True)
                    logger.debug(f"Deleted subtitle file: {path.name}")
                    return True
                return False
            except Exception as e:
                logger.exception(f"Error deleting subtitle file {path}: {e}")
                return False

        try:
            # --- Method 1: Delete tracked subtitle files ---
            for f in self.subtitle_files or []:
                deleted_count[0] += safe_delete(path=Path(f))
            else:
                logger.debug(f"Deleted {deleted_count[0]} of {len(self.subtitle_files)} tracked subtitle files")

            # --- Method 2: Delete new subtitle files not in initial set ---
            new_subtitle_files: Set[Path] = {
                f for f in Path(self.path).rglob("*") if f.suffix in [".vtt", ".srt"] and f not in self.initial_subtitle_files
            }
            for subtitle_file in new_subtitle_files:
                deleted_count[1] += safe_delete(path=subtitle_file)
            else:
                logger.debug(f"Deleted {deleted_count[1]} of {len(new_subtitle_files)} new subtitle files")
        except Exception as e:
            logger.exception(f"Error cleaning subtitle files: {e}")

    def _build_yt_dlp_command(self) -> List[str]:
        """Build the yt-dlp command line with all options for direct execution."""
        yt_dlp_path: str = get_yt_dlp_path()
        # Build the command line array
        cmd: List[str] = [yt_dlp_path]
        logger.debug(f"Using yt-dlp from: {yt_dlp_path}")

        # Add concurrent fragments setting
        if self.concurrent_fragments:
            cmd.extend(["-N", str(self.concurrent_fragments)])
            logger.debug(f"Using {self.concurrent_fragments} concurrent connections")

        # 仅字幕模式：跳过视频/音频下载，只下载 json3 字幕
        if self.subtitle_only_mode:
            return self._build_subtitle_only_command(cmd)

        # Format selection strategy - use format ID if provided or fallback to resolution
        if self.is_playlist:
            # For playlists, specific format_id from the first video often fails for subsequent videos.
            # Instead, we rely on dynamic fallback/resolution limits.
            if self.is_audio_only:
                # For audio-only playlist, let yt-dlp pick best audio.
                cmd.extend(["-f", "bestaudio/best"])
                logger.debug(f"Playlist mode: using dynamic best audio fallback instead of format_id")
            else:
                # If a specific resolution is given, limit to it. Otherwise, select the overall best.
                # The resolution might be e.g. "1920x1080" or "1080". We want the height.
                try:
                    if self.resolution and self.resolution != "default":
                        res_str = str(self.resolution)
                        h = min(map(int, res_str.split('x'))) if 'x' in res_str else int(res_str)
                        cmd.extend(["-S", f"res:{h}"])
                        logger.debug(f"Playlist mode: using resolution limiter -S res:{h}")
                    else:
                        cmd.extend(["-f", "bestvideo+bestaudio/best"])
                        logger.debug("Playlist mode: using dynamic best quality overall")
                except ValueError:
                    cmd.extend(["-f", "bestvideo+bestaudio/best"])
                    logger.debug("Playlist mode: invalid resolution string, using dynamic best quality overall")
        elif self.format_id:
            clean_format_id: str = self.format_id.split("-drc")[0] if "-drc" in self.format_id else self.format_id

            # If the selected format is audio-only, pass it directly.
            if self.is_audio_only:
                cmd.extend(["-f", clean_format_id])
                logger.debug(f"Using audio-only format selection: {clean_format_id}")
            # If the selected format already includes an audio track (progressive), no merge needed.
            elif self.format_has_audio:
                cmd.extend(["-f", clean_format_id])
                logger.debug(f"Using progressive format with bundled audio: {clean_format_id}")
            else:
                cmd.extend(["-f", f"{clean_format_id}+bestaudio/best"])
                logger.debug(f"Using video-only format merged with best audio: {clean_format_id}+bestaudio/best")
        else:
            # If no specific format ID, use resolution-based sorting (-S)
            res_value: str = self.resolution if self.resolution else "720"  # Default to 720p if no resolution specified
            cmd.extend(["-S", f"res:{res_value}"])

        # Force output format if enabled and merging is needed (for video)
        if self.force_output_format and not self.is_audio_only:
            if self.format_has_audio:
                # Progressive format (video with audio) - use remux to convert container
                cmd.extend(["--remux-video", self.preferred_output_format])
                logger.debug(f"Using --remux-video to force progressive format to: {self.preferred_output_format}")
            else:
                # Merging video+audio - force merge output format
                cmd.extend(["--merge-output-format", self.preferred_output_format])
                logger.debug(f"Using --merge-output-format to force merged format to: {self.preferred_output_format}")

        # Force audio format conversion for audio-only downloads
        if self.is_audio_only and self.force_audio_format:
            cmd.append("--extract-audio")
            if self.preferred_audio_format and self.preferred_audio_format != "best":
                cmd.extend(["--audio-format", self.preferred_audio_format])
                logger.debug(f"Using --extract-audio with --audio-format {self.preferred_audio_format} for audio-only download")
            else:
                logger.debug("Using --extract-audio with best quality (no conversion) for audio-only download")
                
        # Add Audio Normalization if enabled (only applies to audio-only downloads)
        if self.audio_normalization and self.is_audio_only:
            # Normalization using FFmpeg filters requires re-encoding the audio stream.
            # If the user selected "Best (No conversion)", yt-dlp attempts to stream copy (-c:a copy),
            # which will cause FFmpeg to crash with "Invalid argument".
            # We fix this by forcing an explicit actual conversion (mp3) if no format was forced.
            if not self.force_audio_format or self.preferred_audio_format == "best":
                if "--extract-audio" not in cmd:
                    cmd.append("--extract-audio")
                cmd.extend(["--audio-format", "mp3"])
                logger.debug("Forced audio format to mp3 since normalization requires re-encoding")

            # Scope the argument specifically to ExtractAudio so it doesn't conflict with other PPs
            cmd.extend(["--postprocessor-args", "ExtractAudio:-af loudnorm=I=-16:LRA=11:TP=-1.5"])
            logger.debug("Added Audio Normalization (--postprocessor-args ExtractAudio:-af loudnorm=...)")

        # Output template with resolution in filename
        # Use string concatenation instead of Path.joinpath to avoid Path object issues
        base_path: str = self.path.as_posix()
        
        # Determine the filename part of the template
        filename_part = self.filename_format if self.filename_format else "%(title)s_%(resolution)s_[%(id)s].%(ext)s"

        if self.is_playlist:
            # Create output template with playlist subfolder
            output_template: str = f"{base_path}/%(playlist_title)s/{filename_part}"
        else:
            # For single files, automatically ignore/remove playlist-specific preamble (like "%(playlist_index)s - ")
            import re
            filename_part = re.sub(r'%\(playlist_index[^)]*\)[a-zA-Z0-9]*\s*(?:[-_]\s*)?', '', filename_part)
            output_template: str = f"{base_path}/{filename_part}"

        cmd.extend(["-o", str(output_template)])

        # Add common options
        cmd.append("--force-overwrites")

        # Add playlist items if specified
        if self.is_playlist and self.playlist_items:
            cmd.extend(["--playlist-items", self.playlist_items])

        # Add subtitle options if subtitles are selected
        if self.subtitle_langs:
            # Subtitles work with both audio-only and video formats
            # For audio-only formats, subtitles will be downloaded as separate files
            cmd.append("--write-subs")

            # Get language codes from subtitle selections
            lang_codes: List[str] = []
            has_auto_generated = False
            for sub_selection in self.subtitle_langs:
                try:
                    # Extract just the language code (e.g., 'en' from 'en - Manual')
                    lang_code = sub_selection.split(" - ")[0]
                    lang_codes.append(lang_code)
                    if "Auto-generated" in sub_selection:
                        has_auto_generated = True
                except Exception as e:
                    logger.exception(f"Could not parse subtitle selection '{sub_selection}': {e}")

            if lang_codes:
                cmd.extend(["--sub-langs", ",".join(lang_codes)])
                if has_auto_generated:
                    cmd.append("--write-auto-subs")  # Include auto-generated subtitles

                # 只要选了字幕就强制使用 json3 格式（单词级时间戳，断句 pipeline 依赖）
                # 不再依赖 llm_segment_enabled 开关 —— 选了字幕就自动走断句 pipeline
                cmd.extend(["--sub-format", "json3"])

                # 注意：json3 会先下载到 self.path（与视频同目录），因为 yt-dlp 的
                # --paths subtitle: 在 -o 含绝对路径时不可靠。断句前我们会按 video_id
                # 精确匹配，把本次下载的 json3 移动到 self.subtitle_temp_dir 隔离处理，
                # 断句完成后清理 temp dir，避免污染共享下载目录。

                # merge_subs: json3 无法被 --embed-subs 直接嵌入，跳过 yt-dlp 的嵌入
                # 断句生成的 SRT 可由用户手动嵌入，或后续用 ffmpeg 嵌入
                if self.merge_subs:
                    logger.info("[Download] merge_subs 与 json3 断句 pipeline 不兼容，跳过 --embed-subs；将生成独立 SRT 文件")

        # Add description saving if enabled
        if self.save_description:
            cmd.append("--write-description")

        # Add chapters embedding if enabled
        if self.embed_chapters:
            cmd.append("--embed-chapters")

        # Add cookies if specified
        if self.cookie_file:
            cmd.extend(["--cookies", str(self.cookie_file)])
        elif self.browser_cookies:
            cmd.extend(["--cookies-from-browser", self.browser_cookies])

        # Add proxy settings if specified
        if self.proxy_url:
            cmd.extend(["--proxy", self.proxy_url])
        
        if self.geo_proxy_url:
            cmd.extend(["--geo-verification-proxy", self.geo_proxy_url])

        # Add rate limit if specified
        if self.rate_limit:
            cmd.extend(["-r", self.rate_limit])

        # Add download section if specified
        if self.download_section:
            cmd.extend(["--download-sections", self.download_section])

            # Add force keyframes option if enabled
            if self.force_keyframes:
                cmd.append("--force-keyframes-at-cuts")

            logger.debug(f"Added download section: {self.download_section}, Force keyframes: {self.force_keyframes}")

        # Add the URL as the final argument
        if self.is_playlist:
            cmd.append("--ignore-errors")
            cmd.append("--no-abort-on-error")
        cmd.append(self.url)

        return cmd

    def _build_subtitle_only_command(self, cmd: List[str]) -> List[str]:
        """构建仅字幕模式的 yt-dlp 命令：跳过视频/音频下载，只下载 json3 字幕。

        json3 是 YouTube 自动字幕的原生格式，包含每个单词的 tOffsetMs，
        是单词级时间戳的来源，配合下游断句方案即可生成精确断句的 SRT。
        """
        logger.info(f"[SubtitleOnly] subtitle_langs={self.subtitle_langs} path={self.path} is_playlist={self.is_playlist}")
        # 跳过视频/音频流下载
        cmd.append("--skip-download")

        # 解析字幕语言选择
        lang_codes: List[str] = []
        has_auto_generated = False
        for sub_selection in self.subtitle_langs:
            try:
                lang_code = sub_selection.split(" - ")[0]
                lang_codes.append(lang_code)
                if "Auto-generated" in sub_selection:
                    has_auto_generated = True
            except Exception as e:
                logger.exception(f"Could not parse subtitle selection '{sub_selection}': {e}")

        # 至少需要写入字幕；用户选了"自动生成"则加 --write-auto-subs，否则只用手动字幕
        if has_auto_generated:
            cmd.append("--write-auto-subs")
        else:
            cmd.append("--write-subs")

        if lang_codes:
            cmd.extend(["--sub-langs", ",".join(lang_codes)])

        # 强制使用 json3 格式以拿到单词级时间戳
        cmd.extend(["--sub-format", "json3"])
        # 不强制转换字幕格式（默认就是不转换；旧版 yt-dlp 不识别 --no-convert-subs）

        # 输出模板：字幕下载到独立的临时目录，避免和共享下载目录下的旧 json3 冲突
        # 断句生成的 SRT 最终会移动到 self.path（用户下载目录）
        base_path: str = self.subtitle_temp_dir.as_posix()
        filename_part = self.filename_format if self.filename_format else "%(title)s_%(resolution)s_[%(id)s].%(ext)s"

        if self.is_playlist:
            output_template: str = f"{base_path}/%(playlist_title)s/{filename_part}"
        else:
            import re as _re
            filename_part = _re.sub(r'%\(playlist_index[^)]*\)[a-zA-Z0-9]*\s*(?:[-_]\s*)?', '', filename_part)
            output_template = f"{base_path}/{filename_part}"

        cmd.extend(["-o", str(output_template)])
        cmd.append("--force-overwrites")

        # 播放列表选项
        if self.is_playlist and self.playlist_items:
            cmd.extend(["--playlist-items", self.playlist_items])
        if self.is_playlist:
            cmd.append("--ignore-errors")
            cmd.append("--no-abort-on-error")

        # Cookie / 代理 / 限速 等通用选项
        if self.cookie_file:
            cmd.extend(["--cookies", str(self.cookie_file)])
        elif self.browser_cookies:
            cmd.extend(["--cookies-from-browser", self.browser_cookies])

        if self.proxy_url:
            cmd.extend(["--proxy", self.proxy_url])
        if self.geo_proxy_url:
            cmd.extend(["--geo-verification-proxy", self.geo_proxy_url])

        if self.rate_limit:
            cmd.extend(["-r", self.rate_limit])

        if self.download_section:
            cmd.extend(["--download-sections", self.download_section])
            if self.force_keyframes:
                cmd.append("--force-keyframes-at-cuts")

        # 最终 URL
        cmd.append(self.url)

        logger.debug(f"Subtitle-only command: {' '.join(shlex.quote(str(a)) for a in cmd)}")
        return cmd

    def run(self) -> None:
        try:
            logger.debug("Starting download thread")

            # 记录下载开始时间，用于 _collect_json3_to_temp_dir 按 mtime 判断
            # 哪些 json3 是本次下载产生的（--force-overwrites 会覆盖旧文件并更新 mtime）
            self.download_start_time: float = time.time()

            # Get initial list of subtitle files to compare later
            self.initial_subtitle_files = set()
            try:
                for file in self.path.rglob("*"):
                    if file.suffix in {".vtt", ".srt", ".json3"}:
                        self.initial_subtitle_files.add(file)
                logger.debug(f"Found {len(self.initial_subtitle_files)} existing subtitle files before download")
            except Exception as e:
                logger.exception(f"Error scanning for initial subtitle files: {e}")

            # Use direct CLI command
            self._run_direct_command()

        except Exception as e:
            # Catch errors during setup
            logger.critical(f"Critical error in download thread: {e}", exc_info=True)
            self.error_signal.emit(f"Critical error in download thread: {e}")
        finally:
            # 兜底清理：确保任何路径下（异常/取消/失败）都会清理字幕临时目录。
            # 正常成功路径下，断句完成后已经清理过；这里是防止异常路径泄漏 temp dir。
            self.cleanup_subtitle_temp_dir()

    def _run_direct_command(self) -> None:
        """Run yt-dlp as a direct command line process instead of using Python API."""
        try:
            self.error_lines = []  # Initialize error capture list
            cmd: List[str] = self._build_yt_dlp_command()

            cmd_str: str = " ".join(shlex.quote(str(arg)) for arg in cmd)
            logger.debug(f"Executing command: {cmd_str}")

            self.status_signal.emit(_("download.starting"))
            self.progress_signal.emit(0)

            # Start the process
            # Extra logic moved to src\utils\sage_constants.py
            # Use start_new_session on Unix to enable process group termination

            popen_kwargs = {
                "stdout": subprocess.PIPE,
                "stderr": subprocess.STDOUT,
                "bufsize": 1,  # Line buffered
                "encoding": "utf-8",
                "errors": "replace",
            }
            
            if sys.platform == "win32":
                popen_kwargs["creationflags"] = SUBPROCESS_CREATIONFLAGS
            else:
                # On Unix, start a new session so we can kill the entire process group
                popen_kwargs["start_new_session"] = True

            self.process = subprocess.Popen(cmd, **popen_kwargs)

            # Process output line by line to update progress
            for line in iter(self.process.stdout.readline, ""):  # type: ignore
                if self.cancelled:
                    # Kill the entire process tree (yt-dlp + ffmpeg children)
                    self._terminate_process_tree(self.process)
                    
                    # Add delay before cleanup to allow file handles to be released
                    time.sleep(2)
                    self.cleanup_partial_files()
                    self.status_signal.emit(_("download.cancelled"))
                    self.finished_signal.emit()
                    return

                # Wait if paused
                while self.paused and not self.cancelled:
                    time.sleep(0.1)

                # Parse the line for download progress and status updates
                self._parse_output_line(line)

            # Wait for process to complete
            return_code: int = self.process.wait()
            logger.info(f"[Download] yt-dlp exit code={return_code}, subtitle_only_mode={self.subtitle_only_mode}, llm_segment_enabled={self.llm_segment_enabled}")
            if hasattr(self, 'error_lines') and self.error_lines:
                logger.warning(f"[Download] captured error_lines (last 5): {self.error_lines[-5:]}")

            # Special handling for specific errors
            # return code 127 typically means command not found
            if return_code == 127:
                self.error_signal.emit(
                    _("errors.ytdlp_not_found_path")
                )
                return

            # 仅字幕模式：即使 yt-dlp 返回非零（如部分警告），只要 temp dir 中存在
            # json3 文件就视为成功，这样后续 LLM 断句仍能执行，不会直接报"下载失败"
            subtitle_only_with_json3 = (
                self.subtitle_only_mode
                and any(self.subtitle_temp_dir.glob('*.json3'))
            )
            if (return_code == 0
                or (self.is_playlist and return_code != 0 and self.current_filename is not None)
                or subtitle_only_with_json3):
                self.progress_signal.emit(100)
                
                # Robust file finding: Always search for the most recent file
                # This handles all post-processing scenarios (merging, remuxing, subtitle embedding, etc.)
                final_file_found = False
                
                try:
                    # First, check if last_file_path exists and is valid
                    if self.last_file_path:
                        last_path = Path(self.last_file_path)
                        if last_path.exists() and last_path.is_file():
                            # File exists at the tracked path
                            self.current_filename = last_path.name
                            final_file_found = True
                            logger.info(f"Found file at tracked path: {self.last_file_path}")
                    
                    # If not found at tracked path, search for the most recent file
                    if not final_file_found:
                        logger.info("Searching for most recent downloaded file...")
                        potential_files = []
                        
                        # Search in download directory and subdirectories (for playlists)
                        for ext in MEDIA_EXTENSIONS:
                            potential_files.extend(self.path.glob(f'*{ext}'))
                            # Also check subdirectories (for playlist downloads)
                            potential_files.extend(self.path.glob(f'*/*{ext}'))
                        
                        if potential_files:
                            # Sort by modification time and get the most recent
                            most_recent = max(potential_files, key=lambda p: p.stat().st_mtime)
                            
                            # Verify it was modified recently (within last 30 seconds to account for post-processing)
                            time_since_modification = time.time() - most_recent.stat().st_mtime
                            
                            if time_since_modification < 30:
                                self.last_file_path = str(most_recent)
                                self.current_filename = most_recent.name
                                final_file_found = True
                                logger.info(f"Found most recent file (modified {time_since_modification:.1f}s ago): {self.last_file_path}")
                            else:
                                logger.warning(f"Most recent file is too old ({time_since_modification:.1f}s), might not be the right one")
                        else:
                            logger.warning("No video/audio files found in download directory")
                    
                except Exception as e:
                    logger.error(f"Error finding final file: {e}", exc_info=True)
                
                # Set completion status
                if return_code != 0:
                    self.status_signal.emit(_("download.completed") + " (with some errors)")
                else:
                    self.status_signal.emit(_("download.completed"))
                
                # merge_subs 不再使用 --embed-subs（json3 不支持嵌入），
                # 因此不需要清理嵌入后的字幕文件；json3 和断句生成的 SRT 均保留

                # 字幕断句 pipeline：只要选了字幕就自动执行（不再需要单独勾选 LLM 断句）
                # 仅字幕模式下，即使 yt-dlp 返回非零，只要 json3 存在也尝试
                has_subtitles = bool(self.subtitle_langs)
                should_segment = has_subtitles and (return_code == 0 or self.subtitle_only_mode)
                if should_segment:
                    # 确保断句配置存在（即使用户没勾 LLM 断句，也用默认配置走 pipeline）
                    if not getattr(self, 'llm_config', None):
                        from .sage_llm_segmenter import _default_llm_config
                        self.llm_config = _default_llm_config()
                    try:
                        self._run_llm_segmentation()
                    except Exception as e:
                        logger.error(f"LLM segmentation failed: {e}")
                    # 断句完成后清理字幕临时目录（SRT 已输出到 self.path）
                    self.cleanup_subtitle_temp_dir()

                self.finished_signal.emit()
            else:
                # Check if it was cancelled
                if self.cancelled:
                    self.status_signal.emit(_("download.cancelled"))
                    self.finished_signal.emit()
                else:
                    # Provide informative error message based on captured output
                    if self.error_lines:
                        # Use the captured error lines (last 2 for context)
                        error_msg = "\n".join(self.error_lines[-2:])
                        self.error_signal.emit(
                            _("errors.ytdlp_failed", error=error_msg)
                        )
                    else:
                        # Fallback to generic return code error
                        self.error_signal.emit(
                            _("errors.download_failed_return_code", return_code=return_code)
                        )

                    # Add delay before cleanup to allow file handles to be released
                    time.sleep(1)
                    self.cleanup_partial_files()

        except Exception as e:
            logger.exception(f"Error in direct command: {e}")
            self.error_signal.emit(_("errors.direct_command_error", error=str(e)))
            # Add delay before cleanup to allow file handles to be released
            time.sleep(1)
            self.cleanup_partial_files()

    def _parse_output_line(self, line: str) -> None:
        """Parse yt-dlp command output to update progress and status."""
        line = line.strip()
        # 把 yt-dlp 全部输出写入日志文件（DEBUG 级别），方便排查问题
        if line:
            logger.debug(f"yt-dlp | {line}")

        # Capture error lines
        if "ERROR:" in line:
            if hasattr(self, 'error_lines'):
                self.error_lines.append(line)

        # Extract filename when the destination line appears
        # Use a slightly more robust regex looking for the start of the line
        dest_match = re.search(r"^\[download\] Destination:\s*(.*)", line)
        if dest_match:
            try:
                filepath = dest_match.group(1).strip()
                self.current_filename = Path(filepath).name
                self.last_file_path = filepath  # Store the full path for later cleanup
                logger.debug(f"Extracted filename: {self.current_filename}")  # DEBUG

                # Check if this is an audio-only download by looking in the previous lines
                is_audio_download = False

                # Look for audio format indicators in the current line or preceding output
                # yt-dlp typically mentions format like "Downloading format 251 - audio only"
                if " - audio only" in line:
                    is_audio_download = True
                # Check if the format ID is mentioned earlier in the line
                format_match = re.search(r"Downloading format (\d+)", line)
                if format_match:
                    format_id = format_match.group(1)
                    logger.debug(f"Detected format ID: {format_id}")
                    # Format IDs for audio typically have different patterns
                    # (like 140, 251 for audio vs 137, 248 for video)
                    # This is just a heuristic since format IDs can vary

                # Determine file type based on extension and context
                ext = Path(self.current_filename).suffix.lower()

                # Check if this is explicitly an audio stream download
                if is_audio_download or "Downloading audio" in line:
                    self.status_signal.emit(_("download.downloading_audio"))
                # Video file extensions with likely video content
                elif ext in VIDEO_EXTENSIONS:
                    self.status_signal.emit(_("download.downloading_video"))
                # Audio file extensions
                elif ext in AUDIO_EXTENSIONS:
                    self.status_signal.emit(_("download.downloading_audio"))
                # Subtitle file extensions
                elif ext in SUBTITLE_EXTENSIONS:
                    self.status_signal.emit(_("download.downloading_subtitle"))
                # Default case
                else:
                    self.status_signal.emit(_("download.downloading"))
            except Exception as e:
                logger.exception(f"Error extracting filename from line '{line}': {e}")
                self.status_signal.emit(_("download.downloading_fallback"))  # Fallback status
            return  # Don't process this line further for speed/ETA

        # Check for specific download types in the output
        if "Downloading video" in line:
            self.status_signal.emit(_("download.downloading_video"))
            return

        elif "Downloading audio" in line:
            self.status_signal.emit(_("download.downloading_audio"))
            return

        # Detect subtitle file creation
        # Look for lines like "[info] Writing video subtitles to: filename.xx.vtt"
        # 同时识别 json3 格式（仅字幕模式 / LLM 断句会用到）
        subtitle_match = re.search(
            r"(?:Writing|Downloading) (?:video )?(?:auto )?subtitles.*?(?:to|:)\s*(.+\.(?:vtt|srt|json3))(?:\s|$)",
            line,
            re.IGNORECASE,
        )
        if subtitle_match:
            subtitle_file = subtitle_match.group(1).strip()

            # Clean up the path - remove any duplicated directory paths
            # Sometimes yt-dlp output contains malformed paths like "dir: dir/file"
            if ":" in subtitle_file and os.name == "nt":  # Windows paths
                # Look for pattern like "C:\path: C:\path\file" and extract the latter
                colon_parts = subtitle_file.split(": ")
                if len(colon_parts) > 1:
                    # Take the last part which should be the actual file path
                    subtitle_file = colon_parts[-1].strip()

            # Show subtitle download message
            self.status_signal.emit(_("download.downloading_subtitle"))
            # Store the subtitle file path for later deletion if merging is enabled
            if self.merge_subs:
                subtitle_path = Path(subtitle_file)
                if not subtitle_path.is_absolute():
                    # If it's a relative path, make it absolute based on current path
                    subtitle_path = self.path.joinpath(subtitle_file)
                self.subtitle_files.append(str(subtitle_path))
                logger.debug(f"Tracking subtitle file for later cleanup: {subtitle_path}")
            return

        # Send status updates based on output line content
        if "Downloading webpage" in line or "Extracting URL" in line:
            self.status_signal.emit(_("download.fetching_info"))
            self.progress_signal.emit(0)
        elif "[download] Destination:" in line:
             # Extract the destination filename
            match = re.search(r"Destination: (.+)", line)
            if match:
                dest_path = match.group(1).strip()
                self.current_filename = Path(dest_path).name
                self.last_file_path = dest_path
                logger.debug(f"Captured destination filename: {self.current_filename}")
        elif "Downloading API JSON" in line:
            self.status_signal.emit(_("download.processing_playlist"))
            self.progress_signal.emit(0)
        elif "Downloading m3u8 information" in line:
            self.status_signal.emit(_("download.preparing_streams"))
            self.progress_signal.emit(0)
        elif "[download] Downloading video " in line:
            self.status_signal.emit(_("download.downloading_video"))
        elif "[download] Downloading audio " in line:
            self.status_signal.emit(_("download.downloading_audio"))
        elif "Downloading format" in line:
            # Try to detect if it's audio or video format
            if " - audio only" in line:
                self.status_signal.emit(_("download.downloading_audio"))
            elif " - video only" in line:
                self.status_signal.emit(_("download.downloading_video"))
            else:
                # Don't emit generic message - format is unclear
                pass

        # Look for download percentage
        percent_match = re.search(r"(\d+\.\d+)%", line)
        if percent_match:
            try:
                percent = float(percent_match.group(1))
                self.progress_signal.emit(percent)
            except (ValueError, IndexError):
                pass

        # Check for download speed and ETA
        if "[download]" in line and "%" in line:
            # Try to extract more detailed status info
            try:
                # Look for speed
                speed_match = re.search(r"at\s+(\d+\.\d+[KMG]iB/s)", line)
                speed_str = speed_match.group(1) if speed_match else "N/A"

                # Look for ETA
                eta_match = re.search(r"ETA\s+(\d+:\d+)", line)
                eta_str = eta_match.group(1) if eta_match else "N/A"

                # Simplify status message to only show the speed and ETA
                status = f"{_('download.speed')}: {speed_str} | {_('download.eta')}: {eta_str}"
                self.update_details.emit(status)
            except Exception as e:
                # If parsing fails, just show basic status (maybe log the error)
                logger.exception(f"Error parsing download details line: {line} -> {e}")
                pass  # Keep basic status emission below if needed, or emit generic details

        # Check for post-processing
        if "[Merger]" in line or "Merging formats" in line:
            self.status_signal.emit(_("download.merging_formats"))
            self.progress_signal.emit(95)
            # Extract the merged output filename
            merger_match = re.search(r"Merging formats into \"(.+?)\"", line)
            if merger_match:
                merged_filepath = merger_match.group(1).strip()
                self.current_filename = Path(merged_filepath).name
                self.last_file_path = merged_filepath
                logger.debug(f"Updated to merged filename: {self.current_filename}")
        elif "Deleting original file" in line:
            self.progress_signal.emit(98)
        elif "has already been downloaded" in line:
            # File already exists - extract filename
            match = re.search(r"(.*?) has already been downloaded", line)
            if match:
                filename = Path(match.group(1)).name
                # Determine file type based on extension for existing file message
                ext = Path(filename).suffix.lower()

                if ext in VIDEO_EXTENSIONS:
                    self.status_signal.emit(f"⚠️ Video file already exists")
                elif ext in AUDIO_EXTENSIONS:
                    self.status_signal.emit(f"⚠️ Audio file already exists")
                elif ext in SUBTITLE_EXTENSIONS:
                    self.status_signal.emit(f"⚠️ Subtitle file already exists")
                else:
                    self.status_signal.emit(f"⚠️ File already exists")

                self.file_exists_signal.emit(filename)
            else:
                logger.info(f"Could not extract filename from 'already downloaded' line: {line}")
                self.status_signal.emit(_("download.file_exists"))  # Fallback status
        elif "Finished downloading" in line:
            self.progress_signal.emit(100)

            # Show completion message based on file type
            if self.current_filename:
                ext = Path(self.current_filename).suffix.lower()

                # Video file extensions
                if ext in VIDEO_EXTENSIONS:
                    self.status_signal.emit(_("download.video_completed"))
                # Audio file extensions
                elif ext in AUDIO_EXTENSIONS:
                    self.status_signal.emit(_("download.audio_completed"))
                # Subtitle file extensions
                elif ext in SUBTITLE_EXTENSIONS:
                    self.status_signal.emit(_("download.subtitle_completed"))
                # Default case
                else:
                    self.status_signal.emit(_("download.completed"))
            else:
                self.status_signal.emit(_("download.completed"))

            self.update_details.emit("")  # Clear details label on completion

    def _collect_json3_to_temp_dir(self) -> None:
        """普通模式下，把本次下载的 json3 文件从 self.path 移动到 temp dir 隔离。

        仅字幕模式的 json3 已经直接下载到 temp dir，无需调用此方法。
        通过 video_id 精确匹配 + initial_subtitle_files 过滤，确保只移动本次下载
        产生的 json3，不会误抓共享下载目录下其他视频或旧测试残留的 json3。
        """
        # 从 URL 提取 video_id
        video_id = ""
        try:
            m = re.search(r'(?:v=|youtu\.be/|/embed/)([A-Za-z0-9_-]{6,})', self.url or "")
            if m:
                video_id = m.group(1)
        except Exception:
            pass

        if not video_id:
            logger.warning("[LLMSeg] 无法从 URL 提取 video_id，跳过 json3 收集")
            return

        # 在 self.path 下找当前视频的 json3（精确匹配 video_id）
        all_candidates = list(self.path.glob(f'*{video_id}*.json3'))
        # 只保留本次下载产生的 json3（mtime > download_start_time）。
        # 不能用 initial_subtitle_files 集合判断：--force-overwrites 会覆盖
        # 同路径旧文件，覆盖后 Path 对象相同，集合比较无法区分新旧。
        start_ts = getattr(self, "download_start_time", 0.0) or 0.0
        candidates: list = []
        skipped_old: list = []
        for p in all_candidates:
            try:
                mtime = p.stat().st_mtime
            except OSError as e:
                logger.warning(f"[LLMSeg] 读取 mtime 失败 {p}: {e}")
                skipped_old.append(p)
                continue
            if mtime > start_ts:
                candidates.append(p)
            else:
                skipped_old.append(p)
        logger.info(
            f"[LLMSeg] 收集 json3 到 temp_dir: video_id={video_id}, "
            f"all={len(all_candidates)}, new={len(candidates)}, "
            f"skipped(old)={[p.name for p in skipped_old]}, "
            f"start_ts={start_ts:.3f}"
        )

        moved = 0
        for src in candidates:
            try:
                dst = self.subtitle_temp_dir / src.name
                # 用 shutil.move 而不是 Path.rename，兼容跨卷移动
                shutil.move(str(src), str(dst))
                moved += 1
                logger.debug(f"[LLMSeg] 移动 {src.name} -> {dst}")
            except Exception as e:
                logger.warning(f"[LLMSeg] 移动 {src} 失败: {e}")
        logger.info(f"[LLMSeg] 共移动 {moved} 个 json3 到 temp_dir")

    def _run_llm_segmentation(self) -> None:
        """Run LLM segmentation post-processing on downloaded json3 files.

        普通模式下，json3 先下载到 self.path，本方法会先按 video_id 精确匹配
        移动到 self.subtitle_temp_dir 隔离处理（避免误抓共享下载目录下其他视频
        的 json3）。仅字幕模式的 json3 已经直接下载到 temp dir，无需移动。
        断句生成的 SRT 输出到 self.path（用户下载目录），断句完成后清理 temp dir。
        """
        from .sage_llm_segmenter import segment_with_llm

        # 普通模式：先把 json3 从 self.path 移到 temp dir 隔离
        if not self.subtitle_only_mode:
            self._collect_json3_to_temp_dir()

        # json3 文件位于独立的临时目录，无需再用 video_id 精确匹配
        temp_dir = self.subtitle_temp_dir
        logger.info(f"[LLMSeg] start. subtitle_only_mode={self.subtitle_only_mode}, temp_dir={temp_dir}, exists={temp_dir.exists()}")
        if not temp_dir.exists():
            logger.warning(f"Subtitle temp dir does not exist: {temp_dir}")
            if self.subtitle_only_mode:
                self.status_signal.emit(_("subtitle_only.no_json3"))
            return

        # 收集需要处理的 json3 文件（temp dir 隔离后是干净的，直接 glob 全部）
        json3_files = sorted(temp_dir.glob('*.json3'))
        logger.info(f"[LLMSeg] json3_files found: {[str(p) for p in json3_files]}")
        if not json3_files:
            logger.info("No json3 subtitle file found for LLM segmentation")
            if self.subtitle_only_mode:
                self.status_signal.emit(_("subtitle_only.no_json3"))
            return

        # 仅字幕模式下的处理中提示
        if self.subtitle_only_mode:
            self.status_signal.emit(_("subtitle_only.segmenting"))

        # 处理每一个 json3 文件
        last_srt_path: Optional[Path] = None
        for idx, json3_path in enumerate(json3_files, 1):
            # 从文件名中尝试推断语言代码（如 title.en.json3 -> en），失败则用 subtitle_langs[0]
            lang = 'en'
            stem = json3_path.stem  # e.g. "title.en"
            parts = stem.split('.')
            if len(parts) >= 2 and len(parts[-1]) <= 8:
                lang = parts[-1]
            elif self.subtitle_langs:
                try:
                    lang = self.subtitle_langs[0].split(" - ")[0]
                except Exception:
                    pass

            # SRT 输出到用户下载目录（self.path），而不是 temp dir
            # 仅字幕模式输出 .srt；普通模式输出 .llm.srt
            if self.subtitle_only_mode:
                # title.en.json3 -> title.en.srt
                srt_filename = f"{stem}.srt"
            else:
                srt_filename = f"{stem}.llm.srt"
            srt_path = self.path / srt_filename

            logger.info(f"[{idx}/{len(json3_files)}] Segmenting: {json3_path} -> {srt_path}")
            if len(json3_files) > 1:
                self.status_signal.emit(f"[{idx}/{len(json3_files)}] {_('subtitle_only.segmenting')}")

            try:
                segment_with_llm(
                    json3_path=json3_path,
                    output_srt_path=srt_path,
                    lang=lang,
                    llm_config=self.llm_config,
                )
                last_srt_path = srt_path
                logger.info(f"Segmentation complete: {srt_path}")
            except Exception as e:
                logger.exception(f"Segmentation failed for {json3_path}: {e}")
                if self.subtitle_only_mode:
                    self.status_signal.emit(_("subtitle_only.segment_failed", error=str(e)))
                # 继续处理下一个文件
                continue

        # 完成提示
        if self.subtitle_only_mode and last_srt_path is not None:
            self.status_signal.emit(_("subtitle_only.complete", path=str(last_srt_path)))
            # 让“打开文件夹”按钮能定位到最后生成的 SRT
            self.last_file_path = str(last_srt_path)
            self.current_filename = last_srt_path.name
        elif not self.subtitle_only_mode:
            self.status_signal.emit(_("llm.complete"))

    def cleanup_subtitle_temp_dir(self) -> None:
        """清理字幕临时目录。

        断句完成后调用，删除整个临时目录树（含 json3 文件）。
        SRT 文件已经输出到 self.path，temp dir 可以安全删除。
        """
        try:
            if self.subtitle_temp_dir.exists():
                shutil.rmtree(self.subtitle_temp_dir, ignore_errors=True)
                logger.info(f"[Download] cleaned subtitle temp dir: {self.subtitle_temp_dir}")
        except Exception as e:
            logger.warning(f"Failed to clean subtitle temp dir: {e}")

    def pause(self) -> None:
        self.paused = True

    def resume(self) -> None:
        self.paused = False

    def cancel(self) -> None:
        self.cancelled = True
        # Terminate the subprocess if it's running
        if self.process:
            try:
                self.process.terminate()
            except Exception:
                pass
