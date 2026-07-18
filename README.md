# SageDLP

下载 YouTube 视频，提取音频，并将原始字幕通过语法感知或 LLM 驱动的分割引擎加工成精美的 SRT 字幕文件。

[English](README.en.md) | [📖 完整文档](docs/ARCHITECTURE.md)

## 快速安装

```bash
pip install sage-dlp
```

需要 Python 3.10-3.14。首次启动时自动下载 FFmpeg、yt-dlp、Deno（JavaScript 运行时），无需手动配置工具链。

## 功能

- **字幕分割引擎。** 两套算法：基于物理规则的引擎（50 CPL 硬限制、语法感知的"不折行桥"分组、稳定合并）和基于 LLM 的分割器（兼容任意 OpenAI 接口）。两者都严格执行时间约束（最少 1.0s 显示、最长 7.0s、目标 14 CPS），不会将冠词、介词或连词孤立在行尾。[→ 详细文档](docs/SUBTITLES.md)

- **LLM 集成。** 完整的 OpenAI 兼容聊天客户端，支持重试、超时、LRU 缓存（256 条）和 JSON 响应校验。`segment_with_llm()` 编排器将 json3 解析、LLM 分割和 SRT 生成串联为一次调用。

- **json3 转 SRT 管线。** 解析 YouTube 专有的 `.json3` 字幕格式，提取为扁平词序列，再通过分割引擎生成时序正确、语法合理的 SRT 文件。

- **自举依赖。** 自动下载并校验 FFmpeg、yt-dlp 的 SHA256 校验和，以及 Deno JavaScript 运行时（用于 YouTube n 挑战求解），无需预装任何工具。[→ 依赖管理](docs/DEPENDENCIES.md)

- **配套浏览器扩展。** Chrome/Edge 扩展自动检测 YouTube 标签页的 Cookie 并推送到本地 HTTP 服务器，无需手动导出 Cookie 文件。[→ Cookie 桥接](docs/COOKIE_BRIDGE.md)

- **丰富的下载 GUI。** 格式选择、播放列表浏览、字幕轨道挑选、音频预览、下载历史——全部基于 PySide6 构建。[→ GUI 文档](docs/GUI.md)

## 快速上手

1. 通过 pip 安装，然后运行 `sage-dlp`。
2. 首次运行自动下载 FFmpeg、yt-dlp 和 Deno。
3. 粘贴 YouTube 链接，应用自动获取可用格式和字幕轨道。
4. 选择格式和字幕语言，点击下载。
5. 如需 LLM 字幕分割，在设置中配置 API 端点和密钥。

## 架构

```
sage_dlp/
├── core/              # 业务逻辑层（下载引擎、断句、依赖管理）
├── gui/               # GUI 层（8 个 Mixin 组合架构）
├── utils/             # 工具层（配置、本地化、日志、Cookie 服务器）
├── languages/         # 本地化文件（中文/英文）
├── browser_ext/       # 浏览器扩展（Cookie 自动推送）
└── assets/            # 图标和音效资源
docs/                  # 详细文档
├── ARCHITECTURE.md    # 架构总览
├── CORE.md            # 核心模块接口
├── GUI.md             # GUI 组件与信号连接
├── SUBTITLES.md       # 字幕断句流水线
├── COOKIE_BRIDGE.md   # Cookie 桥接系统
├── DEPENDENCIES.md    # 依赖管理与启动引导
└── DEVELOPMENT.md     # 开发指南
```

## Cookie 桥接

配套浏览器扩展（位于 `browser_ext/`）监听 YouTube 标签页的 Cookie，将其 POST 到 `127.0.0.1:9876` 的本地 HTTP 服务器。服务器保存为带时间戳的文件并通过 Qt 信号实时通知 GUI 激活。无需手动导出 Cookie 文件。[→ 详细文档](docs/COOKIE_BRIDGE.md)

## Deno 运行时

SageDLP 内嵌了 Deno JavaScript 运行时管理模块（`sage_deno.py`），用于支持 yt-dlp 的 YouTube n 挑战求解。启用 Cookie 认证时，yt-dlp 需要 JS 运行时来获取视频格式信息。Deno 在首次启动时自动下载到应用 bin 目录，也可在「高级选项 → 更新」页面手动管理安装和版本检查。

- **自动安装**：启动时自动检测缺失并后台静默下载
- **版本检查**：在更新器标签页显示当前版本
- **重新安装**：可在 UI 中手动重新下载

## LLM 分割

`sage_llm_segmenter.py` 将 YouTube json3 字幕的原始词序列发送到 OpenAI 兼容 API 进行智能分割。LLM 遵循与规则引擎共享的语法常量（冠词、介词、助动词、限定词、连词），确保两种方法输出语言一致。`SubtitlesProcessor` 支持 `mode='rule'` 和 `mode='llm'` 两种模式，并针对 CJK 字符（1.75x）和韩文（1.5x）进行加权长度计算，实现双语字幕的合理时序。[→ 详细文档](docs/SUBTITLES.md)

## 许可证

MIT。 [GitHub](https://github.com/ID-VerNe/sage-dlp)