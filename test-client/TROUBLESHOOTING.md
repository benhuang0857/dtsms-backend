# 故障排除指南

## Docker Build 失敗: TLS handshake timeout

### 錯誤訊息
```
failed to solve: python:3.11-slim: failed to resolve source metadata for docker.io/library/python:3.11-slim:
failed to do request: Head "https://registry-1.docker.io/v2/library/python/manifests/3.11-slim":
net/http: TLS handshake timeout
```

### 原因
無法連接到 Docker Hub 官方 registry,可能是:
- 網路連線問題
- 防火牆或代理設定
- Docker Hub 在您的地區連線較慢

### 解決方案

#### 方案 1: 配置 Docker Registry Mirror (推薦)

**步驟:**
1. 打開 Docker Desktop
2. 點擊右上角的設置圖示 (Settings/齒輪圖示)
3. 選擇左側的 **"Docker Engine"**
4. 編輯 JSON 配置,添加 registry mirrors:

```json
{
  "builder": {
    "gc": {
      "defaultKeepStorage": "20GB",
      "enabled": true
    }
  },
  "experimental": false,
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com",
    "https://mirror.gcr.io"
  ]
}
```

5. 點擊 **"Apply & Restart"**
6. 等待 Docker 重新啟動
7. 重新執行 `docker-compose build`

#### 方案 2: 使用 VPN 或代理

如果您有 VPN 或代理:
1. 啟用 VPN/代理
2. 在 Docker Desktop 設定中配置代理:
   - Settings → Resources → Proxies
   - 啟用 "Manual proxy configuration"
   - 輸入您的代理地址

#### 方案 3: 重試並增加超時時間

```bash
# 重試幾次
docker-compose build --no-cache

# 或直接使用 docker build
docker build -t dtsms-test-client .
```

#### 方案 4: 使用不同的 Python 版本

編輯 `Dockerfile`,將第 5 行改為:
```dockerfile
FROM python:3.10-slim
# 或
FROM python:3.12-slim
```

#### 方案 5: 手動下載映像

```bash
# 使用 docker pull 手動下載
docker pull python:3.11-slim

# 如果成功,再執行 build
docker-compose build
```

#### 方案 6: 使用替代的 Registry

編輯 `Dockerfile`,使用阿里雲或其他 registry:
```dockerfile
FROM registry.cn-hangzhou.aliyuncs.com/library/python:3.11-slim
```

## 其他常見問題

### 問題: `version` is obsolete

**錯誤訊息:**
```
level=warning msg="docker-compose.yml: `version` is obsolete"
```

**解決方案:**
這只是警告,不影響功能。如果要移除警告,可以刪除 `docker-compose.yml` 第一行的 `version: '3.8'`。

### 問題: 容器無法連接到主機伺服器

**錯誤訊息:**
```
Error: Connection refused
```

**解決方案:**
1. 確認 DTSMS 伺服器正在運行:
   ```bash
   docker ps | findstr dtsms
   ```

2. Windows/Mac 用戶,嘗試改用 `host.docker.internal`:
   ```bash
   docker-compose run --rm test-client \
     /upload/test.txt \
     --host host.docker.internal \
     --port 8888
   ```

3. 檢查防火牆設定

### 問題: SSL/TLS 錯誤

**錯誤訊息:**
```
SSL Error: ...
```

**解決方案:**
1. 確認證書路徑正確
2. 檢查證書有效期
3. 嘗試不使用 TLS 測試:
   ```bash
   docker-compose run --rm test-client \
     /upload/test.txt \
     --no-tls
   ```

## 需要更多協助?

如果以上方案都無法解決問題,請:
1. 檢查 Docker Desktop 版本是否最新
2. 檢查網路連線狀態
3. 查看 Docker Desktop 的 Troubleshoot 選項
4. 查閱 Docker 官方文檔: https://docs.docker.com/
