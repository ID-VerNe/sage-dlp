# Glossary

## Core Concepts

### json3
YouTube 原生字幕格式，包含单词级时间戳（`tOffsetMs`）。SageDLP 的核心数据源，解析后产生 flat_words 序列供断句引擎使用。见 [[Core#sage_json3_parser]]。

### flat_words
json3 解析后的扁平单词列表，每个元素包含 `{word, start, end}` 三个字段。是字幕断句 pipeline 的统一输入格式。

### 字幕断句 Pipeline
从 json3 → flat_words → 断句引擎（规则/LLM）→ SRT 的完整处理流水线。见 [[Core#sage_subtitle_processor]]。

### 仅字幕模式 (Subtitle-Only Mode)
跳过视频/音频下载，仅下载 json3 字幕并执行断句生成 SRT。适用于已有视频文件但缺少精确字幕的场景。

## 断句引擎

### 规则引擎 (Rule Segmenter)
基于物理规则的字幕分割算法：50 CPL 硬限制、语法感知的"不折行桥"分组、稳定合并。见 [[Core#sage_logic_rule]]。

### LLM 引擎 (LLM Segmenter)
基于 OpenAI 兼容 API 的智能分割，使用"七步断句法"：物理断句 → 弹性长度校验 → 标点回溯 → LLM 单点切分 → 语义保底。见 [[Core#sage_logic_llm]]。

### CPS (Characters Per Second)
每秒字符数，字幕阅读速度的度量标准。目标 14 CPS，硬限制 18 CPS。

### CPL (Characters Per Line)
每行最大字符数，硬限制 50。

### 不折行桥 (Unyielding Bridge)
规则引擎中的语法分组机制，防止冠词、介词、连词等在行尾孤立。

## 架构模式

### Mixin 组合
GUI 层使用多继承模式，8 个 mixin 各自封装独立的行为领域，通过 `TYPE_CHECKING` + `self: "SageApp"` 类型注解实现类型安全协作。见 [[Gui#sage_gui_main]]。

### SignalManager
单一 `QObject` 实例，承载所有跨线程信号，作为 mixin 之间的信号代理。见 [[Core#sage_downloader]]。

## 依赖管理

### Deno 运行时
JavaScript 运行时，用于 yt-dlp 的 YouTube n-challenge 求解。使用 Cookie 认证时必需。见 [[Core#sage_deno]]。

### SHA256 校验
yt-dlp 和 FFmpeg 下载后的完整性验证，从官方源下载 SHA256 校验和比对。见 [[Core#sage_yt_dlp]] 和 [[Core#sage_ffmpeg]]。

## 工具层

### Cookie 桥接
浏览器扩展 + 本地 HTTP 服务器（127.0.0.1:9876）的组合，自动将 YouTube Cookie 推送到应用。见 [[Utils#sage_cookie_server]]。

### 设计令牌 (Design Tokens)
QSS 设计系统中的颜色常量：`ACCENT=#2a4a82`, `SUCCESS=#059669`, `SURFACE=#f8fafc`, `TEXT_PRIMARY=#0f172a`。见 [[Gui#sage_stylesheet]]。