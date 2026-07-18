# Core

核心业务逻辑层。包含下载引擎、字幕断句 pipeline、依赖管理和 LLM 客户端。

## sage_downloader — 下载引擎

### 职责

构建 yt-dlp 命令行参数、管理子进程、解析输出、执行断句 pipeline。是整个应用的核心编排器。

### SignalManager

承载所有 mixin 连接到的跨线程信号，作为信号代理：

```python
class SignalManager(QObject):
    update_formats = Signal(list)
    update_status = Signal(str)
    update_progress = Signal(float)
    playlist_info_label_visible = Signal(bool)
    playlist_info_label_text = Signal(str)
    selected_subs_label_text = Signal(str)
    playlist_select_btn_visible = Signal(bool)
    playlist_select_btn_text = Signal(str)
    llm_complete = Signal(str)  # LLM 断句完成 → SRT 路径
```

Reference: [[sage_dlp/core/sage_downloader.py#SignalManager]]

### DownloadThread

QThread 子类，通过 `subprocess.Popen` 执行 yt-dlp，逐行解析输出。

**构造参数**（27 个）：URL、路径、格式 ID、音频/视频/仅字幕模式、字幕语言、播放列表、Cookie、代理、限速等。`llm_config` 和 `llm_segment_enabled` 在构造后通过属性赋值设置。

Reference: [[sage_dlp/core/sage_downloader.py#DownloadThread]]

**关键方法**：

| 方法 | 说明 |
|------|------|
| `_build_yt_dlp_command()` | 构建完整 yt-dlp 命令行（格式选择、字幕、Cookie、代理等） |
| `_build_subtitle_only_command()` | 仅字幕模式命令：`--skip-download --write-subs --sub-format json3` |
| `_run_direct_command()` | 通过 `subprocess.Popen` 执行 yt-dlp，逐行解析输出 |
| `_parse_output_line()` | 解析 yt-dlp 输出行：进度百分比、速度/ETA、文件名、字幕创建、后处理 |
| `_run_llm_segmentation()` | 下载完成后执行字幕断句 pipeline |
| `_collect_json3_to_temp_dir()` | 普通模式下将 json3 文件按 video_id 精确匹配后移动到 temp_dir 隔离 |
| `_terminate_process_tree()` | 跨平台杀死进程树（Windows 用 taskkill /T /F，Unix 用 os.killpg） |
| `cleanup_partial_files()` / `cleanup_subtitle_files()` | 清理残留文件 |
| `cleanup_subtitle_temp_dir()` | 断句完成后清理临时目录 |
| `pause()` / `resume()` | 暂停/恢复下载 |
| `cancel()` | 取消下载并杀死子进程 |

**输出解析模式**（_parse_output_line）：

| 匹配模式 | 操作 |
|---------|------|
| `[download] Destination:` | 提取 `current_filename` 和 `last_file_path` |
| `\d+\.\d+%` | 更新进度条 |
| `at X.XXiB/s` + `ETA X:XX` | 更新速度/ETA 详情 |
| `Writing subtitles to.*\.(vtt\|srt\|json3)` | 跟踪字幕文件 |
| `ERROR:` | 捕获到 `error_lines` |
| `[Merger] Merging formats into` | 后处理合并 |
| `has already been downloaded` | 文件已存在 |
| `Finished downloading` | 完成 |

### 字幕断句触发机制

1. 只要用户选了字幕，下载完成后自动执行断句 pipeline（不再需要单独勾选 LLM 断句）
2. 普通模式：json3 先下载到 `self.path`，然后按 `video_id` 精确匹配移动到 `subtitle_temp_dir` 隔离处理
3. 仅字幕模式：json3 直接下载到 `subtitle_temp_dir`，无需移动
4. 断句生成的 SRT 输出到用户下载目录，完成后清理 temp_dir

### 输出信号

| 信号 | 类型 | 说明 |
|------|------|------|
| `progress_signal` | `Signal(float)` | 下载进度 0-100 |
| `status_signal` | `Signal(str)` | 状态消息 |
| `finished_signal` | `Signal()` | 下载完成 |
| `error_signal` | `Signal(str)` | 错误消息 |
| `file_exists_signal` | `Signal(str)` | 文件已存在 |
| `update_details` | `Signal(str)` | 速度/ETA 等详情 |

Reference: [[sage_dlp/core/sage_downloader.py#DownloadThread]]

---

## sage_subtitle_processor — 字幕处理器

### 职责

字幕断句中枢：接收 json3 解析后的 flat_words，按模式选择断句引擎，执行断句、后处理和 SRT 输出。

### SubtitlesProcessor

```python
class SubtitlesProcessor:
    def __init__(self, segments, lang='en', mode='rule', llm_config=None, callback_progress=None, max_lines=1)
```

**模式**：
- `'rule'` — 规则引擎断句（默认，无需 API Key）
- `'llm'` — LLM 引擎断句（需 OpenAI 兼容 API）
- `'raw'` — 原始输出，不执行断句
- `'semantic'` — 语义引擎（需 spaCy，延迟导入）

**核心常量**（v39 规范）：
- `MAX_CPL = 50` — 每行最大字符数
- `MIN_DURATION_HARD = 1.0` — 最短显示时间
- `MAX_DURATION_HARD = 7.0` — 最长显示时间
- `TARGET_CPS = 14` — 目标阅读速度
- `LIMIT_CPS = 18` — CPS 硬限制
- `GAP_THRESHOLD = 0.083` — 最小间隙

通过 `_apply_segmentation_params()` 支持从 `llm_config` 覆盖这些参数。

Reference: [[sage_dlp/core/sage_subtitle_processor.py#SubtitlesProcessor]]

**关键方法**：

| 方法 | 说明 |
|------|------|
| `calc_len(text)` | VideoLingo 风格加权字符长度计算（CJK 1.75x，韩文 1.5x） |
| `process_segments()` | 主流程：sort → overlap repair → 选择断句引擎 → ASR 清洗 → CPS 归一化 → 反重叠 |
| `_clean_asr_artifacts(text)` | ASR 痕迹清洗：`>>` 指示符、方括号标注、重复词、stutter 修复 |
| `_split_into_two_lines(words)` | 基于 sticky score 的双行分割 |
| `_get_sticky_score_after()` / `_get_break_score_*()` | 语法粘合/断开评分 |

**Compound Fixed 词组**（永不分割）："according to", "as well as", "because of", "in order to" 等约 40 个复合词组。

**ASR 修复规则**（DEFAULT_ASR_REPAIRS）：
- "have to electric" → "have two electric"
- "get car" → "get in the car"
- "that really the case" → "that is really the case"
- 等约 10 个模式

### save_srt

```python
def save_srt(subtitles, filename)
```

将 `[{start, end, text, words}]` 列表写入标准 SRT 格式文件。

Reference: [[sage_dlp/core/sage_subtitle_processor.py#save_srt]]

---

## sage_json3_parser — json3 解析器

### 职责

将 YouTube 原生的 `.json3` 字幕格式解析为 flat_words 序列。

### 数据格式

YouTube json3 结构：
- `events[].tStartMs` — 事件开始时间（毫秒）
- `events[].dDurationMs` — 事件持续时间（毫秒）
- `events[].segs[].utf8` — 文本片段（前导空格 = 新词开始）
- `events[].segs[].tOffsetMs` — 相对于 tStartMs 的偏移（毫秒）

Reference: [[sage_dlp/core/sage_json3_parser.py]]

### parse_yt_json3_to_flat_words

```python
def parse_yt_json3_to_flat_words(json3_data: dict) -> List[Dict[str, Any]]
```

输出：`[{'word': str, 'start': float(seconds), 'end': float(seconds)}, ...]`

**特性**：
- 词边界检测：通过 `segs[].utf8` 的前导空格判断
- 结束时间估计：从下一个词的偏移量或事件的持续时间推断
- 在解析阶段清洗 `>>` 和 `[...]` 标记（_clean_word），确保送入断句引擎的是干净文本
- 解析后对重叠时间戳做修复

### load_json3

```python
def load_json3(path: Path) -> dict
```

从磁盘加载 json3 文件。

---

## sage_logic_rule — 规则断句引擎

### 职责

基于物理规则的 v39 字幕分割算法。不依赖外部 API，纯本地运行。

### RuleSegmenter

```python
class RuleSegmenter:
    def __init__(self, processor)
```

**process 流程**（v39: Physics First, Stability Boost, No Hanging Preps）：

1. **_group_into_natural_units** — 语法感知分组
   - 标点结尾 + 足够间隙 → 切分
   - 从属连词/逻辑桥 → 拉入下一组
   - 专有名词粘合（大写开头连续词）
   - 悬挂词绝对禁止断开（冠词、介词等）
   
2. **_recursive_split_to_events** — 递归分割
   - 50 CPL 物理屏障（`The Wall`，由 `MAX_CPL` 控制）
   - 语法+稳定性评分选择最佳断点
   - 避免产生过小碎片（< 25 chars）

3. **Stabilization Merge** — 稳定合并
   - 悬挂检查：行尾孤立语法词 → 强制合并
   - 稳定性检查：长度 < 28 字符或词数 < 6 → 合并
   - 时长不足 → 合并
   - 间隙 < 0.25s 且总长 < 38 → 合并

Reference: [[sage_dlp/core/sage_logic_rule.py#RuleSegmenter]]

---

## sage_logic_llm — LLM 断句引擎

### 职责

使用 OpenAI 兼容 API 进行智能字幕分割。采用"七步断句法"：物理断句 → 弹性长度校验 → 标点回溯切分 → LLM 单点切分（3 次重试）→ 语义保底。

### LLMSegmenter

```python
class LLMSegmenter:
    def __init__(self, processor)
```

**配置参数**：
- `SOFT_LIMIT = 70` — 理想字符上限（不算末词）
- `HARD_LIMIT = 85` — 绝对字符上限（算上末词）
- `max_workers = 10` — 并发线程数（从 llm_config 读取）

**process 流程**：

1. **_split_by_terminal_punct** — 按 `.?!` 物理断句
2. **_is_acceptable** — 弹性长度校验（70-85 规则）
3. **_find_last_suitable_punctuation** — 从右向左扫描逗号类标点回溯切分
4. **_get_single_cut_llm** — 核心：向 LLM 发送增强版 prompt，要求插入唯一 `[br]` 标记
5. **_accept_llm_cut** — 本地复核：语法合法性、长度合理性、不产生太短片段
6. **_semantic_split_fallback** — 语义权重保底（当 LLM 不切分或拒绝时）
7. 递归迭代收敛

Reference: [[sage_dlp/core/sage_logic_llm.py#LLMSegmenter]]

**LLM Prompt 设计**：
- Role: Subtitle line-break editor
- 任务：在输入文本中插入恰好一个 `[br]` 标记
- 硬规则：不修改原文、不增删词、不改变标点
- 质量规则：优先在短语/从句后分割、避免拆分语法单元

**语法保护**（_is_bad_cut）：禁止在冠词+名词、介词+宾语、助动词+动词、连词后、否定词后、所有格处断开。

线程安全：使用 `ThreadPoolExecutor` 并发处理多个物理块，`max_workers` 可配置。

---

## sage_grammar_constants — 共享语法规则集

### 职责

单一声明语法规则集，被 `RuleSegmenter` 和 `LLMSegmenter` 共同引用。

Reference: [[sage_dlp/core/sage_grammar_constants.py]]

常量集：

| 常量 | 示例 |
|------|------|
| `ARTICLES` | a, an, the |
| `DETERMINERS` | my, your, this, that, each, every |
| `SUBJECTS` | i, you, he, she, it, we, they, there, here |
| `AUXILIARIES` | am, is, are, was, were, can, could, will, would, have, has, had, do, does, did |
| `PREPOSITIONS` | in, on, at, by, with, from, of, to, for, into, onto |
| `CONJUNCTIONS` | and, but, or, so, because, if, when, while, though |
| `NEGATIONS` | not, never, no |

---

## sage_llm_client — LLM API 客户端

### 职责

OpenAI 兼容聊天客户端，支持重试、LRU 缓存、JSON 响应提取。

### LLMClient

```python
class LLMClient:
    def __init__(self, llm_config: Optional[Dict[str, Any]] = None)
```

配置：从 `llm_config` 读取 `url`、`api_key`、`model`、`timeout`、`max_retries`、`temperature`。

**方法**：

| 方法 | 返回 | 说明 |
|------|------|------|
| `chat_text(prompt, system_prompt, timeout, max_retries)` | `str` | 文本响应，最后一次重试失败抛出 `RuntimeError` |
| `chat_json(prompt, system_prompt, validate, timeout, max_retries)` | `dict` | JSON 响应，支持 `response_format: json_object`，可选 validate 函数 |

**重试策略**：
- 指数退避：`2^i` 秒（+1 秒若 429 限流）
- 最大重试次数可配置（默认 3）
- 非 localhost 端点必须配置 API Key

Reference: [[sage_dlp/core/sage_llm_client.py#LLMClient]]

### LRUCache

线程安全 LRU 缓存。类默认 `max_size=128`，全局共享实例 `_GLOBAL_LLM_CACHE` 使用 `max_size=256`。

### JSON 解析

`_parse_json()` 支持三种 JSON 提取方式：直接解析、```json 围栏提取、大括号范围提取。

---

## sage_llm_segmenter — 断句编排入口

### 职责

将 json3 解析 + SubtitlesProcessor + SRT 输出串联为一次调用。

### segment_with_llm

```python
def segment_with_llm(
    json3_path: Path,
    output_srt_path: Path,
    lang: str = 'en',
    llm_config: Optional[Dict[str, Any]] = None,
    progress_callback: Optional[Callable] = None,
) -> List[Dict[str, Any]]
```

流程：Read json3 → json3 → flat_words → 包装为 segments → 选择 mode → SubtitlesProcessor → process_segments → save_srt。

Reference: [[sage_dlp/core/sage_llm_segmenter.py#segment_with_llm]]

### _default_llm_config

返回默认断句配置（rule 模式，不依赖外部 LLM 服务），确保 pipeline 始终能跑通。

### get_json3_path

在输出目录中查找 json3 文件，优先按 video_id 匹配，兜底取最新的 json3 文件。

---

## sage_yt_dlp — yt-dlp 二进制管理

### 职责

管理 yt-dlp 可执行文件的下载、SHA256 校验、发现和更新。

### 函数

| 函数 | 返回 | 说明 |
|------|------|------|
| `check_ytdlp_binary()` | `Optional[Path]` | 在 `APP_BIN_DIR` 中查找 yt-dlp，忽略系统 PATH |
| `check_ytdlp_installed()` | `bool` | 检查 yt-dlp 是否存在并可运行（`--version`） |
| `get_yt_dlp_path()` | `Path` | 返回 yt-dlp 路径，找不到则返回 `"yt-dlp"`（字符串兜底） |
| `verify_ytdlp_sha256(file_path, download_url)` | `bool` | 下载官方 SHA2-256SUMS 并校验文件哈希 |

### DownloadYtdlpThread

| 信号 | 说明 |
|------|------|
| `progress_signal(int)` | 下载进度 0-100 |
| `finished_signal(bool, str)` | 完成：True + 路径 或 False + 错误信息 |

流程：流式下载 → SHA256 校验 → 校验失败自动删除 → Unix 设置可执行权限。

---

## sage_ffmpeg — FFmpeg 管理

### 职责

FFmpeg 的检测、下载和安装。Windows 优先使用 7z 方法，ZIP 为兜底。macOS 使用 Homebrew，Linux 使用包管理器。

### 函数

| 函数 | 返回 | 说明 |
|------|------|------|
| `check_ffmpeg_installed()` | `bool` | 检查 FFmpeg 是否在 PATH 或安装目录中 |
| `get_ffmpeg_path()` | `str \| Path` | 获取 FFmpeg 可执行文件路径 |
| `get_ffmpeg_install_path()` | `Path` | 获取 FFmpeg 安装目录路径 |
| `auto_install_ffmpeg(progress_callback)` | `bool` | 自动安装（分平台） |
| `install_ffmpeg_windows(progress_callback)` | `bool` | Windows 安装——7z → ZIP 兜底 + `setx` 更新 PATH |
| `install_ffmpeg_macos()` | `bool` | macOS 安装——Homebrew → `brew install ffmpeg` |
| `install_ffmpeg_linux()` | `bool` | Linux 安装——apt/dnf/pacman/snap |
| `get_file_sha256(file_path)` | `str` | 计算文件 SHA256 |
| `verify_sha256(file_path, url)` | `bool` | 从 URL 下载预期哈希并校验 |
| `download_file(url, dest, callback)` | `bool` | 通用文件下载 |

---

## sage_deno — Deno 运行时管理

### 职责

管理 Deno JavaScript 运行时的下载和版本检查。yt-dlp 在使用 Cookie 认证时需要 JS 运行时解决 YouTube 的 n-challenge。

### 函数

| 函数 | 返回 | 说明 |
|------|------|------|
| `check_deno_binary()` | `Optional[Path]` | 在 `APP_BIN_DIR` 中查找 deno |
| `check_deno_installed()` | `bool` | 检查 deno 是否存在并可运行 |
| `get_deno_path()` | `Optional[Path]` | 返回 deno 路径 |
| `get_deno_version()` | `str` | 返回版本字符串（如 `"deno 2.9.3"`） |

### DownloadDenoThread

信号：`progress_signal(int)`、`finished_signal(bool, str)`

流程：`requests.get(stream=True)` 下载 ZIP → `ZipFile.testzip()` 完整性检查 → 通过后缀名匹配 deno 可执行文件 → `shutil.move` 到目标位置 → 清理残留。

---

## sage_utils — 通用工具

### 版本缓存

系统使用内存缓存 + 持久化配置来避免每次请求都运行子进程：

```python
_version_cache = {
    "ytdlp": {"version": None, "path": None, "last_check": 0, "path_mtime": 0},
    "ffmpeg": {"version": None, "path": None, "last_check": 0, "path_mtime": 0},
}
```

| 函数 | 说明 |
|------|------|
| `get_ytdlp_version()` | 缓存 yt-dlp 版本 |
| `get_ffmpeg_version()` | 缓存 FFmpeg 版本 |
| `refresh_version_cache(force)` | 手动刷新缓存 |
| `get_ytdlp_version_direct(path)` | 直接运行 `yt-dlp --version` |
| `get_ffmpeg_version_direct()` | 直接运行 `ffmpeg -version` |

### 自动更新

| 函数 | 说明 |
|------|------|
| `should_check_for_auto_update()` | 根据频率设置判断是否需要检查 |
| `check_and_update_ytdlp_auto()` | 执行自动更新检查 |
| `update_yt_dlp()` | 下载并替换 yt-dlp 二进制文件 |

### 其他函数

| 函数 | 说明 |
|------|------|
| `validate_video_url(url, generic_mode)` | URL 校验——支持 YouTube 域名 + 通用模式 |
| `parse_yt_dlp_error(error)` | 错误消息解析为人类可读文本 |
| `check_ffmpeg()` | 检查 FFmpeg 并自动更新 PATH |
| `load_saved_path(instance)` | 从配置加载上次下载路径 |
| `save_path(instance, path)` | 保存下载路径 |