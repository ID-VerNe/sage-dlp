# Project

**Tech Stack**: Python 3.10-3.14 + PySide6 + yt-dlp + SQLite + loguru
**Architecture Pattern**: Mixin 组合架构（GUI 层）+ 分层设计（Core/Utils/GUI）
**Runtime Dependencies**: yt-dlp, FFmpeg, Deno（自动下载 + SHA256 校验）
**Package Name**: `sage-dlp` v5.2.0
**License**: MIT
**Entry Point**: `sage_dlp.main:main` → `sage-dlp` CLI 命令

## One-Line Summary

SageDLP 是一个 YouTube 视频下载与字幕断句桌面应用，基于 Python 3 + PySide6 构建，支持规则引擎和 LLM 双模式字幕分割。

## Modules

- [[Core]] — 业务逻辑层：下载引擎、字幕断句 pipeline、依赖管理（yt-dlp/FFmpeg/Deno）
- [[Gui]] — GUI 层：8 个 Mixin 组合的 QMainWindow 架构
- [[Utils]] — 工具层：线程安全配置、i18n 本地化、Cookie 桥接、日志、下载历史
- [[Dialogs]] — 对话框系统：设置、自定义选项、字幕选择、播放列表选择、更新管理
- [[BrowserExt]] — 浏览器扩展：Chrome/Edge 扩展，自动推送 YouTube Cookie 到本地服务器
- [[Languages]] — 本地化文件：中英文 JSON 翻译文件

## Dependency Graph

依赖关系见 [[Architecture#Module Dependencies]]。

## Key Design Decisions

1. **Mixin 组合而非继承树**：GUI 层使用 8 个独立 mixin 通过 `TYPE_CHECKING` 类型注解引用宿主 `SageApp`，避免循环导入，同时实现完全类型安全。
2. **字幕断句双模式**：规则引擎（50 CPL 硬限制、语法感知分组）和 LLM 引擎（OpenAI 兼容 API）共享同一套语法常量，确保输出语言风格一致。
3. **自举依赖管理**：首次启动自动下载 yt-dlp、FFmpeg、Deno，所有二进制文件带 SHA256 校验，无需用户手动配置工具链。
4. **json3 原生格式优先**：YouTube 的 json3 格式包含单词级时间戳，是断句 pipeline 的数据源头，比传统的 vtt/srt 格式更精确。
5. **仅字幕模式**：支持跳过视频/音频下载，仅下载 json3 字幕并执行断句，适用于已有视频文件但缺少精确字幕的场景。