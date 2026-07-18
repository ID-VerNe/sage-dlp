# Dialogs

对话框子包（sage_dlp/gui/sage_gui_dialogs/）。`__init__.py` 重新导出所有对话框类。

## sage_dialogs_base — 共享基础

### 职责

提供所有对话框共享的设计令牌、QSS 辅助函数和基础组件。

**设计令牌常量**：`ACCENT`, `SURFACE`, `BORDER`, `TEXT_PRIMARY` 等，与 `sage_stylesheet.py` 保持一致。

**QSS 辅助函数**：`dialog_base_qss()`, `primary_button_qss()`, `checkbox_qss()`, `groupbox_qss()` 等。

**基础组件**：
- `empty_state_widget(title, desc, icon)` — 空状态占位组件
- `LogWindow` — 日志查看对话框
- `SystemInfoThread` — 系统信息收集线程

---

## sage_dialogs_settings — 下载设置对话框

### DownloadSettingsDialog

三标签页设置界面：

| 标签页 | 设置项 |
|--------|--------|
| 通用 | 下载路径、限速（KB/s / MB/s）、并发分片数、通用模式 |
| 格式 | 强制输出格式 + 首选格式、强制音频格式 + 首选格式、音频归一化、默认质量、优先语言 |
| 文件 | 文件名格式模板 |

### AutoUpdateSettingsDialog

- 启用/禁用自动更新
- 更新频率选择
- 手动检查更新按钮
- 当前版本和状态显示

---

## sage_dialogs_custom — 自定义选项对话框

### CustomOptionsDialog

五标签页配置界面：

| 标签页 | 设置项 |
|--------|--------|
| Cookie | Cookie 源选择（浏览器提取/文件）、浏览器类型、配置文件路径、记住设置 |
| 代理 | 主代理 URL（支持 http/socks5）、Geo 验证代理、清除按钮 |
| LLM | 模式选择（LLM/规则）、API URL、API Key、模型名称、温度、高级参数（超时/重试/并发/段参数） |
| 更新器 | FFmpeg 版本检查(FFmpegCheckThread)、Deno 状态/安装、应用更新通道切换(稳定版/测试版)、自动更新配置 |
| 语言 | 语言选择下拉框、切换时显示重启提示 |

**LLM 配置标签页的完整参数**：
- Segmentation Mode: LLM / Rule
- API Server: URL, API Key, Model
- Temperature (0.0-2.0)
- Advanced: Timeout, Max Retries, Max Workers
- Segmentation Parameters: Soft Limit, Hard Limit, Target CPS, CPS Limit

---

## sage_dialogs_selection — 选择对话框

### SubtitleSelectionDialog

- 显示所有可用字幕语言列表
- 默认选中英文字幕（en/zh-hans/zh 过滤）
- 多选 + 搜索过滤
- 确认后返回选中列表

### PlaylistSelectionDialog

- 显示播放列表中的所有视频
- 搜索过滤
- 全选/取消全选
- 确认后返回选中条目范围字符串

---

## sage_dialogs_update — 更新相关对话框

| 导出 | 说明 |
|------|------|
| `VersionCheckThread` | yt-dlp 版本检查线程 |
| `YTDLPUpdateDialog` | 带进度条的 yt-dlp 更新对话框 |
| `UpdateThread` | 更新执行线程 |
| `AutoUpdateThread` | 自动更新线程（定时检查） |

---

## sage_dialogs_updater — 更新器标签

### UpdaterTabWidget

嵌入 `CustomOptionsDialog` 的更新器标签页组件：

| 组件/方法 | 说明 |
|-----------|------|
| `FFmpegCheckThread` | FFmpeg 版本检查线程 |
| `check_ffmpeg_version()` | 获取 FFmpeg 版本 |
| `compare_versions()` | 版本比较逻辑 |
| `_refresh_deno_status()` | 刷新 Deno 状态显示 |
| `_install_deno()` | 下载/重新安装 Deno |

---

## sage_dialogs_ffmpeg — FFmpeg 安装线程

### FFmpegInstallThread

| 信号 | 说明 |
|------|------|
| `finished(bool)` | 安装完成 |
| `progress(str)` | 安装进度消息（如下载进度、校验状态、解压状态） |

后台静默安装 FFmpeg，用于 `StartupMixin` 的自动安装流程。