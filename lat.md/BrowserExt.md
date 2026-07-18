# BrowserExt

浏览器扩展（sage_dlp/browser_ext/）。Chrome/Edge 配套扩展，自动检测 YouTube 标签页的 Cookie 并推送到本地 HTTP 服务器。

## 工作原理

```
YouTube 标签页 Cookie 变化
  → background.mjs 监听 chrome.cookies.onChanged
    → 获取所有 Cookie → 格式化为 Netscape 格式
      → POST http://127.0.0.1:9876/api/cookies
        → CookieServer 保存到文件 → Qt 信号通知 GUI
```

## 文件结构

```
browser_ext/src/
├── manifest.json           # 扩展清单
├── background.mjs          # 后台服务：Cookie 变化监听 + HTTP 推送
├── popup.html / .css / .mjs  # 弹出窗口 UI
└── modules/                # Cookie 获取/格式化/保存逻辑
```

## 核心特性

- **自动检测**：监听 `chrome.cookies.onChanged` 事件，YouTube 标签页 Cookie 变化时自动触发
- **无需手动导出**：用户无需手动导出 Cookie 文件，扩展自动推送到本地服务器
- **兼容性**：Chrome 和 Edge 均可使用
- **隐私安全**：仅推送 YouTube 域名 Cookie，本地服务器绑定 127.0.0.1

## 配置

扩展需要与桌面应用的 Cookie 服务器端口一致（默认 9876），参见 [[Utils#sage_cookie_server]]。