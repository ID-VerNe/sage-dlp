# SageDLP Cookie Bridge Extension

This is a modified fork of [Get cookies.txt LOCALLY](https://github.com/kairi003/Get-cookies.txt-LOCALLY) that **auto-sends cookies** to the SageDLP desktop application via a local HTTP server.

## How it works

1. The extension reads cookies from the current tab (same as the original).
2. In `background.mjs`, whenever the badge counter updates (`cookies.onChanged`, `tabs.onUpdated`, etc.), it serializes the cookies to Netscape format and POSTs them to `http://127.0.0.1:9876/api/cookies`.
3. SageDLP's `CookieServer` (a threaded HTTP server in `sage_dlp/utils/sage_dlp_cookie_server.py`) receives the POST, saves the cookie text to `{APP_DATA_DIR}/cookies/`, and signals the main window to auto-activate the cookie file.
4. The popup UI is fully preserved — the user can still export/download cookies manually.

## Installation

### In Chrome / Edge / Brave:

1. Open `chrome://extensions`
2. Enable **Developer mode** (top right toggle)
3. Click **Load unpacked**
4. Select the `sage_dlp/browser_ext/src` folder

### In Firefox:

Firefox does not support `fetch()` from service workers to localhost in the same way. The Firefox variant is not yet implemented.

## Changes from upstream

- `manifest.json`: Renamed to "SageDLP Cookie Bridge", added `http://127.0.0.1:9876/*` to `host_permissions`.
- `background.mjs`: Added `postCookiesToServer()` that serializes cookies to Netscape format and POSTs them to the local SageDLP server on every badge update.
- Original download/clipboard/popup functionality is completely unchanged.

## Port configuration

The default port is **9876** — matching the default in `sage_dlp/utils/sage_dlp_cookie_server.py`. To change it, update both:

1. `background.mjs` → `SAGEDLP_SERVER_URL` constant
2. `sage_dlp/utils/sage_dlp_cookie_server.py` → `COOKIE_SERVER_PORT`