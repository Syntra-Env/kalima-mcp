# WebDriver Binaries (Local)

This folder is for local WebDriver binaries used by Tauri E2E tests.

- Windows: place `msedgedriver.exe` here if you don’t want to put it on `PATH`.
- The repo ignores `*.exe` and `*.zip` in this folder.

The Tauri E2E runner will automatically use `tools/webdriver/msedgedriver.exe` if present, or you can set `MSEDGEDRIVER_PATH`.

