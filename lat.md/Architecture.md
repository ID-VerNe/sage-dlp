# Architecture

## Three-Layer Architecture

SageDLP 使用经典的三层架构，外加一个工具层：

```
┌─────────────────────────────────────────────────────┐
│  GUI Layer (sage_dlp/gui/)                          │
│  SageApp (QMainWindow + 8 Mixin)                    │
│  ├── UIMixin — 窗口构建/信号连接                      │
│  ├── StartupMixin — 启动引导/依赖安装/关闭事件         │
│  ├── DownloadMixin — 下载生命周期编排                  │
│  ├── AnalysisMixin — URL 分析（yt-dlp 元数据获取）     │
│  ├── VideoInfoMixin — 视频信息/缩略图                  │
│  ├── FormatTableMixin — 格式表格/过滤                  │
│  ├── DialogOpsMixin — 对话框启动器/Cookie 桥接         │
│  └── WidgetAnimationMixin — 动画/弹窗/遮罩            │
├─────────────────────────────────────────────────────┤
│  Core Layer (sage_dlp/core/)                         │
│  ├── Download Engine (sage_downloader)               │
│  ├── Subtitle Pipeline (sage_subtitle_processor)     │
│  │   ├── Rule Segmenter (sage_logic_rule)            │
│  │   └── LLM Segmenter (sage_logic_llm)              │
│  ├── json3 Parser (sage_json3_parser)                │
│  ├── LLM Client (sage_llm_client)                    │
│  └── Dependency Managers (yt-dlp/FFmpeg/Deno)        │
├─────────────────────────────────────────────────────┤
│  Utils Layer (sage_dlp/utils/)                       │
│  ├── ConfigManager — 线程安全 JSON 配置               │
│  ├── CookieServer — HTTP Cookie 桥接服务器            │
│  ├── LocalizationManager — i18n 本地化                │
│  ├── HistoryManager — SQLite 下载历史                 │
│  ├── Logger — loguru 日志系统                         │
│  └── Constants — 路径/URL/扩展名常量                  │
└─────────────────────────────────────────────────────┘
```

## Module Dependencies

```
main.py
  ├── gui/sage_gui_main (SageApp)
  │   ├── gui/sage_gui_ui (UIMixin)
  │   ├── gui/sage_gui_startup (StartupMixin)
  │   │   ├── core/sage_yt_dlp (DownloadYtdlpThread)
  │   │   ├── core/sage_ffmpeg (FFmpegInstallThread, auto_install_ffmpeg)
  │   │   └── core/sage_deno (DownloadDenoThread)
  │   ├── gui/sage_gui_download (DownloadMixin)
  │   │   ├── core/sage_downloader (DownloadThread, SignalManager)
  │   │   │   ├── core/sage_yt_dlp (get_yt_dlp_path)
  │   │   │   └── core/sage_llm_segmenter (segment_with_llm)
  │   │   │       ├── core/sage_json3_parser (parse_yt_json3_to_flat_words)
  │   │   │       └── core/sage_subtitle_processor (SubtitlesProcessor, save_srt)
  │   │   │           ├── core/sage_logic_rule (RuleSegmenter)
  │   │   │           ├── core/sage_logic_llm (LLMSegmenter)
  │   │   │           │   └── core/sage_llm_client (LLMClient, LRUCache)
  │   │   │           └── core/sage_grammar_constants (语法规则集)
  │   │   └── utils/sage_history_manager (HistoryManager)
  │   ├── gui/sage_gui_analysis (AnalysisMixin)
  │   │   └── core/sage_yt_dlp (get_yt_dlp_path)
  │   ├── gui/sage_gui_video_info (VideoInfoMixin)
  │   ├── gui/sage_gui_format_table (FormatTableMixin)
  │   ├── gui/sage_gui_dialogs_ops (DialogOpsMixin)
  │   │   ├── gui/sage_gui_dialogs/* (全部对话框)
  │   │   └── utils/sage_cookie_server (CookieServer)
  │   ├── gui/sage_gui_animations (WidgetAnimationMixin)
  │   ├── utils/sage_config_manager (ConfigManager)
  │   ├── utils/sage_constants (路径/URL/扩展名常量)
  │   ├── utils/sage_localization (LocalizationManager, _)
  │   └── utils/sage_logger (logger)
  └── utils/sage_logger (logger)
```

## Key Data Flow

### 下载流程

```
URL 输入 → 点击 Analyze
  → AnalysisThread (yt-dlp --dump-single-json)
  → _on_analysis_complete → 更新 UI（视频信息/格式表格/字幕列表）
  → 选择格式 + 字幕 → 点击 Download
  → DownloadThread (yt-dlp subprocess)
    → 下载完成 → _run_llm_segmentation (json3 → SRT)
    → 1. 普通模式：json3 按 video_id 精确匹配 → 移动到 temp_dir 隔离
    → 2. 仅字幕模式：json3 直接下载到 temp_dir
    → parse_yt_json3_to_flat_words → SubtitlesProcessor → save_srt
  → 完成信号 → 历史记录 + 通知音
```

### 启动流程

```
UI 显示后 100ms → _perform_startup_checks()
  ├─ 检查 FFmpeg → 缺失则后台静默安装
  ├─ 检查 yt-dlp → 缺失则后台静默下载（SHA256 校验）
  ├─ 检查 Deno → 缺失则后台静默下载
  ├─ check_for_updates() → 检查应用更新（GitHub Release API）
  ├─ cookie_server.start() → 启动 Cookie 桥接（127.0.0.1:9876）
  └─ 2s 后 → check_auto_update_ytdlp() → yt-dlp 自动更新检查
```

## Cross-Thread Communication

所有工作线程通过 Qt 信号与主线程通信：

| 线程类 | 文件 | 信号 | 用途 |
|--------|------|------|------|
| `AnalysisThread` | `sage_gui_analysis.py` | `analysis_complete`, `analysis_error`, `status_update`, `progress_update`, `playlist_info_*` | 分析结果 |
| `DownloadThread` | `sage_downloader.py` | `progress_signal`, `status_signal`, `finished_signal`, `error_signal`, `file_exists_signal`, `update_details` | 下载进度 |
| `DownloadYtdlpThread` | `sage_yt_dlp.py` | `progress_signal(int)`, `finished_signal(bool, str)` | yt-dlp 下载 |
| `DownloadDenoThread` | `sage_deno.py` | `progress_signal(int)`, `finished_signal(bool, str)` | Deno 下载 |
| `UpdateCheckThread` | `sage_gui_update_check.py` | `update_available` | 应用版本检查 |
| `AutoUpdateThread` | `sage_dialogs_update.py` | `update_finished` | yt-dlp 自动更新 |
| `FFmpegInstallThread` | `sage_dialogs_ffmpeg.py` | `finished(bool)`, `progress(str)` | FFmpeg 安装 |
| `ThumbnailDownloadThread` | `sage_gui_video_info.py` | `finished(bytes)`, `error(str)` | 缩略图下载 |

`SignalManager`（`sage_downloader.py`）作为代理——一个单一 `QObject` 承载所有由 mixin 连接到的命名信号。