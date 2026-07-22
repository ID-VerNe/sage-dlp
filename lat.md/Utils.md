# Utils

工具层（sage_dlp/utils/）。包含线程安全配置管理、i18n 本地化、Cookie 桥接、日志系统和下载历史。

## sage_config_manager — 配置管理器

### 职责

线程安全的中央配置管理。通过 JSON 文件持久化设置，支持点号嵌套键访问。

Reference: [[sage_dlp/utils/sage_config_manager.py#ConfigManager]]

### ConfigManager

```python
class ConfigManager:
    _lock: threading.RLock = threading.RLock()
    _config_file: Path = APP_CONFIG_FILE
    _settings: Dict[str, Any] = {}
```

线程安全通过 `RLock` 保证；支持点号键嵌套读写；修改自动持久化。

**方法**：

| 方法 | 说明 |
|------|------|
| `get(key)` | 点号键获取值（如 `"cached_versions.ytdlp.last_check"`） |
| `set(key, value)` | 设置值并保存 |
| `delete(key)` | 删除键 |
| `_load()` | 从 JSON 文件加载，损坏/缺失时使用默认值 |
| `_save()` | 保存到 JSON 文件 |

**默认配置关键项**（约 40 项，以下为主要项）：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `download_path` | `~/Downloads` | 下载目录 |
| `generic_mode` | `true` | 通用模式（支持非 YouTube 网站） |
| `cookie_source` | `"browser"` | Cookie 源：browser / file |
| `cookie_browser` | `"chrome"` | 浏览器选择 |
| `language` | `"zh"` | 界面语言 |
| `llm_enabled` | `false` | LLM 断句开关 |
| `llm_mode` | `"rule"` | 断句模式：llm / rule |
| `llm_url` | `"http://localhost:8000"` | LLM API URL |
| `llm_model` | `"gpt-4.1"` | 模型名称 |
| `llm_temperature` | `0.1` | 温度参数 |
| `llm_max_workers` | `10` | 并发线程数 |
| `cached_versions` | `{ytdlp, ffmpeg}` | 版本缓存 |

---

## sage_localization — 本地化管理器

### 职责

线程安全的 i18n 本地化系统，支持动态切换语言、英文兜底、点号键访问。

Reference: [[sage_dlp/utils/sage_localization.py#LocalizationManager]]

### LocalizationManager

```python
class LocalizationManager:
    _current_language = "zh"
    _languages_dir = Path(__file__).parent.parent / "languages"
```

特性：线程安全（RLock）；英文内嵌兜底字符串（约 160 条）；JSON 语言文件加载；动态切换语言无需重启。

**方法**：

| 方法 | 说明 |
|------|------|
| `initialize(language_code)` | 初始化本地化系统 |
| `get_text(key, **kwargs)` | 获取本地化文本，支持格式化参数 |
| `set_language(code)` | 切换语言 |
| `get_available_languages()` | 扫描语言目录获取可用语言列表 |
| `get_current_language()` | 获取当前语言代码 |

```
# 便捷函数
def _(key: str, **kwargs) -> str:
    return LocalizationManager.get_text(key, **kwargs)
```

### 兜底策略

1. 当前语言 JSON 文件
2. 内嵌英文兜底字符串（`_fallback_strings`，分类存储：buttons, dialogs, tabs, download, formats, errors, llm 等）
3. 返回 key 本身

---

## sage_cookie_server — Cookie 桥接服务器

### 职责

轻量级线程化 HTTP 服务器（127.0.0.1:9876），接收浏览器扩展 POST 的 Cookie 数据，保存到时间戳文件并通过 Qt 信号通知 GUI。**无状态设计**——去重逻辑由扩展端负责，服务端仅做接收→保存→通知。

Reference: [[sage_dlp/utils/sage_cookie_server.py#CookieServer]]

### 架构

```
浏览器扩展 (background.mjs)
  → 300ms 防抖 + 字符串比较去重（扩展端）
    → POST http://127.0.0.1:9876/api/cookies （仅 cookie 内容变化时）
      → _CookieRequestHandler (BaseHTTPRequestHandler)
        → _save_cookies() → 保存到 {APP_DATA_DIR}/cookies/cookies_{host}_{timestamp}.txt
        → CookieServer.cookies_received.emit(file_path, url) → Qt 主线程
```

### CookieServer

```python
class CookieServer(QObject):
    cookies_received: Signal = Signal(str, str)  # (cookie_file, url)
```

方法：`start(port)`、`stop()`、`is_running`、`port`、`url`

### _CookieRequestHandler

支持：POST /api/cookies。请求体符合 `CookiePayload` 数据契约：

```python
@dataclass
class CookiePayload:
    cookies: str = ""    # Netscape 格式 Cookie 文本
    url: str = ""        # 来源页面 URL
    source: str = "extension"  # 来源标识
```

也支持：OPTIONS 预检（CORS）、GET 404。

Cookie 文件名格式：`cookies_{host}_{timestamp}.txt`（host 从 URL 提取，做安全文件名清洗）。

### _ThreadedHTTPServer

组合 `Thread` + `HTTPServer`，`allow_reuse_address = True`，daemon 线程。

### 去重设计

去重由扩展端（[[BrowserExt]]）在发送前完成：300ms 防抖 + 字符串比较（`cookiesText === _lastCookiesText`）。服务端不保存状态，每次 POST 都直接写入文件。这避免了服务端维护 MD5 缓存带来的线程安全隐忧，也让服务器可以被多个扩展实例独立访问。

---

## sage_logger — 日志系统

### 职责

基于 loguru 的日志系统。统一管理日志输出目标、格式和级别。

核心功能：日志文件轮转、控制台输出、异常追踪。整个应用通过 `from ..utils.sage_logger import logger` 使用单一日志器。

---

## sage_history_manager — 下载历史管理器

### 职责

基于 SQLite 的线程安全下载历史管理。支持 CRUD、搜索、JSON 历史自动迁移。

Reference: [[sage_dlp/utils/sage_history_manager.py#HistoryManager]]

### HistoryManager

```python
class HistoryManager:
    _lock = threading.RLock()
    _db_file = APP_DATA_DIR / "sage_dlp_history.db"
```

**数据库表结构**：

```sql
CREATE TABLE IF NOT EXISTS history (
    id TEXT PRIMARY KEY,
    title TEXT, url TEXT, channel TEXT,
    file_path TEXT, download_date TEXT,
    file_size INTEGER, thumbnail_url TEXT,
    format_id TEXT, resolution TEXT,
    is_audio_only INTEGER, duration TEXT,
    options TEXT, timestamp REAL
);
```

索引：`idx_timestamp`（DESC）、`idx_title`、`idx_channel`、`idx_url`

**方法**：

| 方法 | 说明 |
|------|------|
| `add_entry(title, url, ...)` | 添加下载记录 |
| `get_all_entries(limit)` | 获取所有记录（最近优先） |
| `get_entry(entry_id)` | 获取单条记录 |
| `remove_entry(entry_id)` | 删除记录 |
| `clear_history()` | 清空历史 |
| `search_entries(query)` | 按标题/频道/URL 搜索 |

**迁移**：首次运行时自动将旧的 JSON 历史文件迁移到 SQLite，原文件重命名为 `.json.bak`。

---

## sage_constants — 路径/URL/扩展名常量

### 职责

集中定义跨模块共享的常量：资产路径、平台检测、下载 URL、子进程创建标志、文件扩展名。

Reference: [[sage_dlp/utils/sage_constants.py]]

### 内容

**平台相关**：
- `OS_NAME` — 操作系统检测
- `SUBPROCESS_CREATIONFLAGS` — Windows `CREATE_NO_WINDOW`
- `APP_DATA_DIR` / `APP_BIN_DIR` / `APP_CONFIG_FILE` — 路径常量

**下载 URL**：
- `YTDLP_DOWNLOAD_URL` / `YTDLP_SHA256_URL`
- `FFMPEG_7Z_DOWNLOAD_URL` / `FFMPEG_ZIP_DOWNLOAD_URL` / SHA256 URLs
- `DENO_DOWNLOAD_URL`

**文件类型集合**：
- `VIDEO_EXTENSIONS` — mp4, webm, mkv, avi, mov, flv
- `AUDIO_EXTENSIONS` — mp3, m4a, aac, ogg, wav, flac, opus
- `SUBTITLE_EXTENSIONS` — vtt, srt, ass, ssa, json3
- `MEDIA_EXTENSIONS` — 视频 + 音频的并集

**资产路径**：
- `ICON_PATH` / `SOUND_PATH`
- `get_asset_path()` — 开发/打包双模式路径解析（支持 PyInstaller 和 cx_Freeze）

---

## sage_flow_layout — 自动换行布局

### 职责

自定义 Qt FlowLayout，支持控件的自动换行排列。用于格式控制按钮区域（视频/音频/仅字幕按钮 + 复选框），窗口调整大小时自动重排布局。