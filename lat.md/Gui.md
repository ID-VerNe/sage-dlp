# Gui

GUI 层（sage_dlp/gui/）。基于 Mixin 组合架构的 PySide6 桌面应用界面。

## sage_gui_main — 组合根

### SageApp

```python
class SageApp(QMainWindow, UIMixin, StartupMixin, DownloadMixin,
              DialogOpsMixin, WidgetAnimationMixin, FormatTableMixin,
              VideoInfoMixin, AnalysisMixin):
```

组合根。仅包含 `__init__` 方法，所有行为由 8 个 mixin 提供。

Reference: [[sage_dlp/gui/sage_gui_main.py#SageApp]]

**__init__ 职责**：
- 初始化本地化系统（默认中文）
- 加载保存的下载路径和配置
- 创建 `SignalManager` 实例
- 初始化音频播放器（QMediaPlayer + QAudioOutput）
- 启动 Cookie 服务器（CookieServer）
- 调用 `init_ui()` 构建界面
- 延迟 100ms 执行启动检查（_perform_startup_checks）
- 连接视频/音频/仅字幕模式按钮信号

---

## UIMixin — 窗口构建 (sage_gui_ui.py)

### 职责

构建完整主窗口布局、信号连接、UI 状态管理。

**UI 布局结构**：

```
QMainWindow
  └── centralWidget (QVBoxLayout)
      ├── URL Row (QHBoxLayout: url_input, paste_button, analyze_button)
      ├── Video Info Container (QVBoxLayout)
      │   └── Media Info (QHBoxLayout: thumbnail_label + Video Info VBox)
      │       ├── 标题/频道/观看/点赞/日期/时长 标签
      │       └── Subtitle Row (选择字幕按钮 + 已选标签)
      ├── Playlist Section (播放列表信息 + 选择/保存按钮)
      ├── Format Controls (FlowLayout)
      │   ├── 视频/音频/仅字幕模式按钮 (可选中 toggle)
      │   └── 合并字幕/保存缩略图/描述/章节/LLM 断句 复选框
      ├── Format Table (QStackedWidget: 空状态 ↔ 格式表格)
      ├── Download Buttons (自定义选项/设置/下载/暂停/取消)
      └── Progress Section (进度条 + 状态标签 + 打开文件夹)
```

### 信号连接

| 信号 | 连接至 | 说明 |
|------|--------|------|
| `url_input.returnPressed` | `analyze_url` | Enter 键分析 |
| `url_input.textChanged` | `_on_url_text_changed` | 启用/禁用按钮 |
| `paste_button.clicked` | `paste_url` | 粘贴 |
| `analyze_button.clicked` | `analyze_url` | 分析 |
| `video_button.clicked` | `filter_formats` + `handle_mode_change` | 视频模式 |
| `audio_button.clicked` | `filter_formats` + `handle_mode_change` | 音频模式 |
| `subtitle_only_button.clicked` | `filter_formats` + `handle_mode_change` | 仅字幕模式 |
| `download_btn.clicked` | `start_download` | 开始下载 |
| `signals.update_formats` | `update_format_table` | 格式数据 |
| `signals.update_status` | `set_status_message_animated` | 状态消息 |
| `signals.update_progress` | `update_progress_bar` | 进度条 |

---

## StartupMixin — 启动与生命周期 (sage_gui_startup.py)

### 启动流程

```
UI 显示后 100ms → _perform_startup_checks()
  ├─ 检查 FFmpeg → 缺失则后台静默安装 (_silent_ffmpeg_thread)
  ├─ 检查 yt-dlp → 缺失则后台静默下载 (_silent_ytdlp_thread)
  ├─ 检查 Deno → 缺失则后台静默下载 (_silent_deno_thread)
  ├─ check_for_updates() → 检查应用更新
  ├─ cookie_server.start() → 启动 Cookie 桥接服务器
  └─ 2s 后 → check_auto_update_ytdlp() → 自动更新检查
```

### 应用更新对话框

从 GitHub Release API 获取 changelog（Markdown → HTML），提供下载按钮跳转到发布页。

### 关闭事件

停止所有线程（分析/下载/自动更新/静默安装）→ 停止 Cookie 服务器 → 保存窗口几何状态。

---

## DownloadMixin — 下载生命周期 (sage_gui_download.py)

### 流程

```
start_download()
  ├─ 验证 URL + 路径
  ├─ 收集所有参数（格式、字幕、Cookie、代理、限速等）
  ├─ 创建 DownloadThread
  │   ├─ 配置 llm_segment_enabled / llm_config
  │   └─ 连接信号 → progress/status/finished/error/file_exists
  └─ thread.start()
```

### 关键方法

| 方法 | 说明 |
|------|------|
| `start_download()` | 启动下载——验证 → 收集参数 → 创建线程 → 连接信号 → 启动 |
| `download_finished()` | 完成处理——恢复控件、显示完成消息、打开文件夹按钮、保存历史、播放通知音 |
| `download_error(error)` | 错误处理——恢复控件、显示错误消息 |
| `update_progress_bar(value)` | 平滑动画进度更新（0.1% 精度） |
| `toggle_pause()` | 暂停/恢复 |
| `cancel_download()` | 取消下载 |
| `file_already_exists(filename)` | 文件已存在处理 |
| `open_download_folder()` | 打开下载文件夹并高亮文件（Windows: `explorer /select`） |

---

## AnalysisMixin — URL 分析 (sage_gui_analysis.py)

### AnalysisThread 信号

| 信号 | 用途 |
|------|------|
| `status_update(str)` | 状态消息 |
| `progress_update(int)` | 进度百分比 |
| `playlist_info_visible(bool)` | 播放列表信息可见性 |
| `playlist_info_text(str)` | 播放列表文案 |
| `playlist_select_btn_visible(bool)` | 播放列表选择按钮可见性 |
| `playlist_select_btn_text(str)` | 按钮文案 |
| `analysis_complete(dict)` | 分析结果数据 |
| `analysis_error(str)` | 错误消息 |
| `analysis_finished()` | 线程完成 |

### 分析流程

```
analyze_url()
  ├─ 验证 URL (validate_video_url)
  ├─ 停止已有分析线程
  ├─ 创建 AnalysisThread
  ├─ 连接所有信号
  └─ thread.start()
    └─ run():
        ├─ yt-dlp --dump-single-json --flat-playlist --no-warnings
        ├─ 解析 JSON
        ├─ 播放列表 → 额外获取第一个视频详细格式
        ├─ 组装 result_data dict
        └─ analysis_complete.emit(result_data)
```

### 分析结果数据结构

```python
result_data = {
    "is_playlist": bool,
    "playlist_info": dict | None,
    "playlist_entries": list,
    "video_info": dict | None,
    "all_formats": list,
    "available_subtitles": dict,
    "available_automatic_subtitles": dict,
    "thumbnail_url": str | None,
}
```

### Deno 警告

使用浏览器 Cookie 且 Deno 未安装时，`_check_deno_and_emit_warning()` 在状态栏显示提示。

---

## VideoInfoMixin — 视频信息 (sage_gui_video_info.py)

| 方法 | 说明 |
|------|------|
| `setup_video_info_section()` | 构建缩略图 + 视频信息 + 字幕选择区域 |
| `setup_playlist_info_section()` | 构建播放列表信息标签 |
| `update_video_info(info)` | 填充视频元数据（标题/频道/时长/日期/点赞数） |
| `open_subtitle_dialog()` | 打开字幕选择对话框 |
| `download_thumbnail(url)` | 异步下载缩略图（ThumbnailDownloadThread） |

---

## FormatTableMixin — 格式表格 (sage_gui_format_table.py)

| 方法 | 说明 |
|------|------|
| `setup_format_table()` | 创建 QTableWidget（9 列/6 列播放列表模式） |
| `filter_formats()` | 按视频/音频按钮状态过滤行可见性 |
| `update_format_table(formats)` | 信号接收器——重建完整格式表 |
| `get_selected_format()` | 返回当前选中格式信息 |
| `get_quality_label(info)` | 根据分辨率/码率返回质量标签 |

**表格列**（普通模式 9 列）：选择、质量（颜色编码 4 级）、扩展名、分辨率、文件大小、编解码器、音频、FPS、HDR。播放列表模式缩减为 6 列。

---

## WidgetAnimationMixin — 动画 (sage_gui_animations.py)

| 方法 | 说明 |
|------|------|
| `animate_widget_fade_in(widget, duration)` | 淡入（QGraphicsOpacityEffect + QPropertyAnimation） |
| `animate_widget_fade_out(widget, duration)` | 淡出并隐藏 |
| `set_widget_visible_animated(widget, visible)` | 带淡入淡出的可见性切换 |
| `animate_widget_shake(widget)` | 抖动——输入错误提示（5px, 300ms） |
| `set_status_message_animated(message)` | 状态文字淡出 → 换文 → 淡入 |
| `run_dialog_with_blur(dialog)` | 半透明遮罩层 + 模态对话框 |

---

## DialogOpsMixin — 对话框启动器 (sage_gui_dialogs_ops.py)

| 方法 | 说明 |
|------|------|
| `_initialize_cookie_settings_from_config()` | 从 ConfigManager 恢复 Cookie 设置 |
| `show_download_settings_dialog()` | 打开下载设置对话框 |
| `show_custom_options()` | 打开自定义选项（Cookie/代理/语言/LLM/更新器） |
| `open_playlist_selection_dialog()` | 打开播放列表选择对话框 |
| `save_playlist_to_file()` | 将播放列表保存为 txt/m3u/csv/json |
| `_on_cookies_received_from_extension(path, url)` | 浏览器扩展 Cookie 自动导入槽 |

---

## sage_stylesheet — 设计系统

QSS 设计系统，延迟构建（`_build_all()`）后赋值给类常量。

**设计令牌**：

| 常量 | 值 | 用途 |
|------|-----|------|
| `ACCENT` | `#2a4a82` | 主色调蓝 |
| `SUCCESS` | `#059669` | 绿色 |
| `SURFACE` | `#f8fafc` | 页面背景 |
| `TEXT_PRIMARY` | `#0f172a` | 主文字色 |

QSS 片段：`StyleSheet.MAIN`, `ANALYZE_BUTTON`, `PROGRESS_BAR`, `SECONDARY_BUTTON`, `WARNING_BUTTON`, `DANGER_BUTTON` 等。

---

## sage_smooth_tab_widget — 平滑标签切换

提供带平滑动画效果的标签切换组件。