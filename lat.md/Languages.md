# Languages

本地化文件（sage_dlp/languages/）。JSON 格式的翻译文件，当前支持中英文。

## 文件列表

| 文件 | 说明 |
|------|------|
| `zh.json` | 中文（简体）翻译 |
| `en.json` | 英文翻译 |

## 结构

JSON 文件使用嵌套键组织，与 `LocalizationManager.get_text(key)` 的点号语法对应：

```json
{
  "app": {
    "title": "SageDLP",
    "version": "v{version}"
  },
  "buttons": {
    "download": "下载",
    "analyze": "分析"
  },
  "download": {
    "starting": "正在准备下载...",
    "completed": "下载完成！"
  },
  "errors": {
    "ytdlp_failed": "错误：yt-dlp 失败：{error}"
  }
}
```

## 兜底机制

当当前语言的 JSON 文件中找不到某个键时，系统会回退到 [[Utils#sage_localization]] 中内嵌的英文兜底字符串（约 400+ 条，覆盖所有常用的 UI 文本）。

## 语言切换

通过设置界面或 `LocalizationManager.set_language(code)` 切换语言。切换后需要重启应用才能完全生效。

可用语言列表通过扫描 `languages/` 目录下的 JSON 文件自动发现。