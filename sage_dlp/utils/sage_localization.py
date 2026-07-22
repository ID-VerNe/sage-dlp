"""
Localization Manager Module
==========================

This module provides centralized localization support for SageDLP application.
It handles loading language files, switching languages, and retrieving localized strings.

Features
--------
- Thread-safe operations for getting localized text
- Fallback to English when translation is missing
- Support for multiple languages via JSON files
- Dynamic language switching without restart
- Nested key support with dot notation

Usage
-----
from .sage_localization import LocalizationManager

# Get localized text
text = LocalizationManager.get_text("download.ready")
button_text = LocalizationManager.get_text("buttons.download")

# Change language
LocalizationManager.set_language("zh")

# Get available languages
languages = LocalizationManager.get_available_languages()
"""

import json
import threading
from pathlib import Path
from typing import Any, Dict

from .sage_logger import logger


class LocalizationManager:
    """
    Thread-safe localization manager for SageDLP.

    Handles loading, caching, and retrieving localized strings from JSON language files.
    """

    _lock = threading.RLock()
    _current_language = "zh"
    _languages: Dict[str, Dict[str, Any]] = {}
    _languages_dir = Path(__file__).parent.parent / "languages"

    # Fallback English strings embedded in code
    _fallback_strings = {
        "app": {
            "title": "SageDLP",
            "version": "v{version}",
            "ready": "Ready"
        },
        "buttons": {
            "download": "Download",
            "pause": "Pause",
            "resume": "Resume",
            "cancel": "Cancel",
            "browse": "Browse",
            "clear": "Clear",
            "ok": "OK",
            "apply": "Apply",
            "close": "Close",
            "save_playlist": "Save Playlist As",
            "custom_options": "Custom Options",
            "open_folder": "Open folder location",
            "analyze": "Analyze",
            "paste_url": "Paste URL",
            "video": "Video",
            "audio_only": "Audio Only",
            "change_path": "Change Path"
        },
        "dialogs": {
            "custom_options": "Custom Options",
            "settings": "Settings",
            "select_folder": "Select Download Folder",
            "ytdlp_log_title": "yt-dlp Log",
            "select_subtitles": "Select Subtitles",
            "filter_languages_placeholder": "Filter languages (e.g., en, es)...",
            "filter_playlist_placeholder": "Filter videos..."
        },
        "tabs": {
            "cookies": "Login with Cookies",
            "custom_command": "Custom Command",
            "proxy": "Proxy",
            "language": "Language",
            "updater": "Updater"
        },
        "selection": {
            "none_selected": "0 selected",
            "one_selected": "1 category selected",
            "count_selected": "{count} selected"
        },
        "status": {
            "ready": "Ready",
            "file_exists": "File already exists",
            "video_file_exists": "Video file already exists",
            "audio_file_exists": "Audio file already exists",
            "subtitle_file_exists": "Subtitle file already exists",
            "thumbnail_saved": "Thumbnail saved: {filename}",
            "thumbnail_error": "Thumbnail error: {error}",
            "thumbnail_no_image": "No thumbnail available to save"
        },
        "main_ui": {
            "url_placeholder": "Enter YouTube video or playlist URL",
            "url_placeholder_generic": "Enter video or playlist URL from any supported site",
            "settings_tooltip": "Current Path: {path}\nSpeed Limit: {speed_limit}",
            "speed_limit_none": "None",
            "select_subtitles": "Select Subtitles",
            "merge_subtitles": "Merge Subtitles",
            "save_thumbnail": "Save Thumbnail",
            "save_description": "Save Description",
            "embed_chapters": "Embed Chapters",
            "analyze_first_tooltip": "Please analyze the video first",
            "audio_mode_disabled": "Not available in audio-only mode",
            "select_subtitles_first": "Please select subtitles first"
        },
        "language": {
            "select_language": "Select Language:",
            "current_language": "Current language: {language}",
            "restart_required": "Language changes will take effect after restarting the application.",
            "english": "English",
            "chinese": "中文 (简体) (Chinese Simplified)"
        },
        "download": {
            "preparing": "Preparing your download...",
            "completed": "Download completed!",
            "video_completed": "Video download completed!",
            "audio_completed": "Audio download completed!",
            "subtitle_completed": "Subtitle download completed!",
            "please_set_path": "Please set a download path using 'Change Path'",
            "please_enter_url": "Please enter a URL",
            "please_enter_url_and_path": "Please enter URL and set download path",
            "please_select_format": "Please select a format"
        },
        "formats": {
            "show_formats": "Show formats:",
            "select": "Select",
            "quality": "Quality",
            "extension": "Extension",
            "resolution": "Resolution",
            "file_size": "File Size",
            "codec": "Codec",
            "audio": "Audio",
            "fps": "FPS",
            "hdr": "HDR",
            "will_merge_audio": "Will merge audio",
            "has_audio": "Has Audio",
            "audio_only": "Audio Only",
            "best_4k": "Best (4K)",
            "best_2k": "Best (2K)",
            "high_1080p": "High (1080p)",
            "high_720p": "High (720p)",
            "medium_480p": "Medium (480p)",
            "low_quality": "Low Quality",
            "best_audio": "Best Audio",
            "high_audio": "High Audio",
            "medium_audio": "Medium Audio",
            "low_audio": "Low Audio",
            "no_formats_title": "No Video Analyzed",
            "no_formats_desc": "Enter a URL above and click Analyze to see available formats"
        },
        "errors": {
            "download_failed_return_code_conflict": "Download failed with return code {return_code}. This may be due to a conflict with multiple yt-dlp installations. Try uninstalling any system-installed yt-dlp (e.g. through snap or apt) and restart the application.",
            "download_failed_return_code": "Download failed with return code {return_code}",
            "direct_command_error": "Error in direct command: {error}",
            "generic_error": "Error: {error}",
            "timeout": "Operation timed out",
            "ytdlp_not_found": "Error: yt-dlp executable not found.",
            "no_data_returned": "Error: No data returned from yt-dlp",
            "no_format_info": "Error: No format information available.",
            "parse_failed": "Error: Failed to parse yt-dlp output: {error}",
            "playlist_no_videos": "Error: Playlist contains no valid videos.",
            "private_video": "This video might be private. Please use cookies.",
            "ytdlp_failed": "Error: yt-dlp failed: {error}"
        },
        "about": {
            "open_logs": "Logs",
            "logs_tooltip": "Open application logs folder",
            "refresh": "Refresh",
            "title": "About SageDLP",
            "version": "Version {version}",
            "system_info": "System Information",
            "loading": "Loading system information...",
            "refreshing": "Refreshing...",
            "detected": "Detected",
            "missing": "Missing",
            "not_available": "Not Available"
        },
        "llm": {
            "tab_title": "LLM Smart Segmentation",
            "help_text": "Configure LLM-powered subtitle segmentation. Requires an OpenAI-compatible API endpoint (local or cloud).",
            "mode_title": "Segmentation Mode",
            "mode_llm": "LLM Mode (Recommended, better segmentation)",
            "mode_rule": "Rule Mode (No API Key required)",
            "api_title": "API Server",
            "api_url": "API URL:",
            "api_url_placeholder": "http://localhost:8000",
            "api_url_tooltip": "Base URL for your OpenAI-compatible API endpoint",
            "api_key": "API Key:",
            "api_key_placeholder": "sk-... (leave empty for local endpoints)",
            "api_key_tooltip": "Authentication key. Leave empty for local endpoints without auth",
            "model_group": "Model",
            "model": "Model:",
            "model_placeholder": "gpt-4.1",
            "model_tooltip": "The LLM model name to use for segmentation",
            "temperature": "Temperature:",
            "temperature_tooltip": "Controls randomness (0=deterministic, 2=very random)",
            "temperature_unit": "(0.0-2.0)",
            "adv_group": "Advanced",
            "timeout": "Timeout:",
            "timeout_tooltip": "Maximum seconds to wait for each API call",
            "timeout_unit": "seconds",
            "max_retries": "Max Retries:",
            "max_retries_tooltip": "Number of times to retry failed API calls",
            "max_workers": "Max Workers:",
            "max_workers_tooltip": "Max concurrent API requests",
            "workers_unit": "threads",
            "seg_title": "Segmentation Parameters",
            "soft_limit": "Soft Limit:",
            "soft_limit_tooltip": "Target segment character count before splitting",
            "hard_limit": "Hard Limit:",
            "hard_limit_tooltip": "Hard maximum characters per segment (overrides soft)",
            "limit_unit": "chars",
            "target_cps": "Target CPS:",
            "target_cps_tooltip": "Target characters per second for ideal subtitle timing",
            "limit_cps": "CPS Limit:",
            "limit_cps_tooltip": "Maximum characters per second threshold",
            "cps_unit": "chars/s",
            "checkbox": "LLM Smart Segmentation",
            "checkbox_tooltip": "Use LLM to segment subtitles (requires LLM config first)"
        },
        "welcome_dialog": {
            "title": "Welcome to SageDLP",
            "desc": "SageDLP is ready to start downloading. yt-dlp, ffmpeg and other dependencies will be downloaded automatically.",
            "config_location": "Configuration & Data Directory",
            "config_hint": "Settings, cache, logs and downloaded binaries are stored here.",
            "extension": "Browser Extension (Optional)",
            "extension_desc": "Install the Chrome/Edge extension to auto-sync cookies from your browser — no more manual cookie file exports.",
            "extension_steps": "<ol style='margin: 4px 0 0 20px; padding: 0; font-size: 12px; color: #334155;'><li>Open Chrome/Edge and go to <code>chrome://extensions</code></li><li>Turn on <b>Developer mode</b> (top-right corner)</li><li>Click <b>Load unpacked</b> and select the extension folder</li><li>Done! Cookies will sync automatically</li></ol>",
            "open_extension_folder": "Open Extension Folder",
            "view_tutorial": "View Tutorial",
            "get_started": "Get Started"
        }
    }

    @classmethod
    def _ensure_languages_dir(cls) -> None:
        """Ensure the languages directory exists."""
        cls._languages_dir.mkdir(exist_ok=True)

    @classmethod
    def _load_language(cls, language_code: str) -> Dict[str, Any]:
        """
        Load a language file from disk.

        Args:
            language_code: The language code (e.g., 'en', 'es')

        Returns:
            Dictionary containing the language strings, or empty dict if not found
        """
        language_file = cls._languages_dir / f"{language_code}.json"

        if not language_file.exists():
            logger.warning(f"Language file not found: {language_file}")
            return {}

        try:
            with open(language_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Failed to load language file {language_file}: {e}")
            return {}

    @classmethod
    def _get_nested_value(cls, data: Dict[str, Any], key: str) -> Any:
        """
        Get a nested value from dictionary using dot notation.

        Args:
            data: Dictionary to search in
            key: Dot-separated key (e.g., "app.title")

        Returns:
            The value if found, None otherwise
        """
        parts = key.split(".")
        value = data

        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return None

        return value

    # @lat: [[Utils#sage_localization]]
    @classmethod
    def get_text(cls, key: str, **kwargs) -> str:
        """
        Get localized text for the given key.

        Args:
            key: Dot-separated key for the text (e.g., "app.title")
            **kwargs: Format parameters for the text

        Returns:
            Localized text, with fallback to English if not found
        """
        with cls._lock:
            # Load current language if not cached
            if cls._current_language not in cls._languages:
                cls._languages[cls._current_language] = cls._load_language(cls._current_language)

            # Try to get from current language
            current_lang_data = cls._languages.get(cls._current_language, {})
            text = cls._get_nested_value(current_lang_data, key)

            # Fallback to embedded English strings
            if text is None:
                text = cls._get_nested_value(cls._fallback_strings, key)

            # Final fallback to key itself
            if text is None:
                logger.warning(f"Localization key not found: {key}")
                text = key

            # Format the text with provided parameters
            if kwargs and isinstance(text, str):
                try:
                    text = text.format(**kwargs)
                except (KeyError, ValueError) as e:
                    logger.warning(f"Failed to format localized text '{key}': {e}")

            return str(text)

    @classmethod
    def set_language(cls, language_code: str) -> None:
        """
        Set the current language.

        Args:
            language_code: The language code to set (e.g., 'en', 'es')
        """
        with cls._lock:
            if language_code != cls._current_language:
                cls._current_language = language_code
                # Clear cache to force reload
                cls._languages.clear()
                logger.info(f"Language set to: {language_code}")

    @classmethod
    def get_current_language(cls) -> str:
        """Get the current language code."""
        return cls._current_language

    @classmethod
    def get_available_languages(cls) -> Dict[str, str]:
        """
        Get available languages from the languages directory.

        Returns:
            Dictionary mapping language codes to display names
        """
        cls._ensure_languages_dir()

        available_languages = {"en": cls.get_text("language.english")}

        # Scan for language files
        for language_file in cls._languages_dir.glob("*.json"):
            lang_code = language_file.stem
            if lang_code != "en":  # Skip English as it's already added
                # Try to get language display name from the file
                lang_data = cls._load_language(lang_code)
                display_name = cls._get_nested_value(lang_data, "language.display_name")
                if display_name:
                    available_languages[lang_code] = display_name
                else:
                    # Fallback display name
                    available_languages[lang_code] = lang_code.upper()

        return available_languages

    @classmethod
    def initialize(cls, language_code: str = "zh") -> None:
        """
        Initialize the localization system.

        Args:
            language_code: Initial language code to use
        """
        with cls._lock:
            cls._ensure_languages_dir()
            cls.set_language(language_code)
            logger.info(f"Localization system initialized with language: {language_code}")


# Convenience function for getting localized text
def _(key: str, **kwargs) -> str:
    """
    Convenience function to get localized text.

    Args:
        key: Dot-separated key for the text
        **kwargs: Format parameters

    Returns:
        Localized text
    """
    return LocalizationManager.get_text(key, **kwargs)