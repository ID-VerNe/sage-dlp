# BrowserExt

浏览器扩展（sage_dlp/browser_ext/）。Chrome/Edge 配套扩展，监听当前标签页的 Cookie 变化，按需推送到本地 HTTP 服务器。

## 工作原理

```
事件源（4 个）:
  chrome.cookies.onChanged       → handleCookieChanged()  → postCookiesToServer()
  chrome.tabs.onUpdated           ┐
  chrome.tabs.onActivated         ├→ updateBadgeCounter()   → 仅更新 badge 数字
  chrome.windows.onFocusChanged   ┘

postCookiesToServer() 链路:
  URL hostname 取 debounce 定时器（300ms）
    → clearTimeout + setTimeout 防抖（快速切换标签时只发最后一次）
      → getAllCookies({url, partitionKey})  → serializeNetscape()
        → 字符串比较去重: cookiesText === _lastCookiesText（全局变量，跨 host 共享，相同文本则跳过）
          → POST http://127.0.0.1:9876/api/cookies
            → CookieServer 保存到文件 → Qt 信号通知 GUI
```

## 文件结构

```
browser_ext/src/
├── manifest.json           # 扩展清单（MV3，permissions: cookies + activeTab + downloads + notifications）
├── background.mjs          # 后台服务：事件分离 + 防抖 + 去重 + HTTP 推送
├── background.html         # 备用后台页面
├── popup.html / .css / .mjs / .dark.css / -options.css  # 弹出窗口 UI
├── table-nowrap.js         # 表格样式辅助
├── modules/
│   ├── get_all_cookies.mjs # Cookie 获取（支持 partitionKey 双通道合并）
│   ├── cookie_format.mjs   # 格式转换工具
│   └── save_to_file.mjs    # 文件保存
├── iconfont/               # Material Icons 图标字体
└── images/                 # 扩展图标 PNG + 捐赠按钮 SVG
```

## 核心特性

- **事件分离**：只有 `cookies.onChanged` 触发 POST；`tabs.on*` 和 `windows.onFocusChanged` 仅更新 badge 数字，避免标签切换时刷屏推送
- **300ms 防抖**：`setTimeout`/`clearTimeout` 按 host 分组计时，快速连续事件聚合为一次 POST。防抖只延迟发送，不改变最终行为
- **字符串去重**：`cookiesText === _lastCookiesText` 全局变量跨 host 比较，内容相同则跳过 POST（比 MD5 更简单，数据已在内存中）
- **错误日志**：`console.warn` 替代静默吞异常，便于排查同步失败
- **兼容性**：Chrome 和 Edge 均可使用
- **隐私安全**：`getAllCookies` 始终传入当前标签页 URL 和 `partitionKey`，仅推送该域名 Cookie；本地服务器绑定 127.0.0.1
- **注意**：`updateBadgeCounter` 内部也调用 `getAllCookies`，每次 badge 更新都有 cookie 读取成本，但无网络开销

## 去重设计取舍

去重放在扩展端而非服务端，原因：发送端在源头就拦截重复数据，比服务端接收后再丢弃更高效（省掉 fetch 往返 + JSON 解析 + 响应开销）。服务端 [[Utils#sage_cookie_server]] 回归纯粹职责：接收 → 保存 → 通知，无状态。

## 配置

扩展需要与桌面应用的 Cookie 服务器端口一致（默认 9876），参见 [[Utils#sage_cookie_server]]。

## 其他监听器

除 Cookie 同步外，`background.mjs` 还注册了以下监听器：

- `runtime.onInstalled` — 扩展更新后弹出桌面通知，显示版本号，提供 GitHub Releases / Uninstall 按钮
- `notifications.onButtonClicked` — 处理通知按钮点击，跳转 GitHub Release 页或执行卸载
- `runtime.onMessage` — 接收 Firefox 弹出窗口的 `saveToFile` 请求，写入文件系统