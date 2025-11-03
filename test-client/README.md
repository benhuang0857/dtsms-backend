# DTSMS Test Client (Docker Version)

這是 DTSMS 的測試客戶端 Docker 版本,用於測試檔案上傳功能。

## 目錄結構

```
test-client/
├── docker-compose.yml    # Docker Compose 配置
├── Dockerfile           # Docker 映像定義
├── test-client.py       # 測試客戶端腳本
├── upload/              # 放置要上傳的檔案
└── README.md           # 本文件
```

## 前置準備

1. 確保 DTSMS 伺服器正在運行 (在 `webserver` 目錄)
2. 創建 `upload` 目錄並放入測試檔案:
   ```bash
   mkdir upload
   echo "Hello DTSMS!" > upload/test.txt
   ```

## 使用方式

### 方法 1: 使用 Docker Compose (推薦)

#### 基本上傳 (不使用 mTLS)
```bash
# 編輯 docker-compose.yml 中的 command 參數
docker-compose run --rm test-client /upload/test.txt --host 127.0.0.1 --port 8888
```

#### 使用 mTLS 上傳
```bash
docker-compose run --rm test-client \
  /upload/test.txt \
  --host 127.0.0.1 \
  --port 8888 \
  --client-cert /certs/client.crt \
  --client-key /certs/client.key \
  --ca-cert /certs/ca.crt
```

#### 一鍵執行 (使用預設配置)
```bash
docker-compose up
```

### 方法 2: 直接使用 Docker

#### 建立映像
```bash
docker build -t dtsms-test-client .
```

#### 執行客戶端

**Bash / Linux / macOS:**
```bash
# 基本用法 (無 TLS)
docker run --rm \
  --network host \
  -v $(pwd)/upload:/upload \
  dtsms-test-client /upload/test.txt --host localhost --port 8888 --no-tls

# 使用 mTLS (推薦) - 多行版本
docker run --rm \
  --network host \
  -v $(pwd)/upload:/upload \
  -v $(pwd)/certs:/certs:ro \
  dtsms-test-client \
  /upload/test.txt \
  --host localhost \
  --port 8888 \
  --client-cert /certs/client.crt \
  --client-key /certs/client.key \
  --ca-cert /certs/ca.crt

# 使用 mTLS (推薦) - 一行版本
docker run --rm --network host -v $(pwd)/upload:/upload -v $(pwd)/certs:/certs:ro dtsms-test-client /upload/test.txt --host localhost --port 8888 --client-cert /certs/client.crt --client-key /certs/client.key --ca-cert /certs/ca.crt
```

**PowerShell / Windows:**
```powershell
# 基本用法 (無 TLS)
docker run --rm `
  --network host `
  -v ${PWD}/upload:/upload `
  dtsms-test-client /upload/test.txt --host localhost --port 8888 --no-tls

# 使用 mTLS (推薦) - 多行版本
docker run --rm `
  --network host `
  -v ${PWD}/upload:/upload `
  -v ${PWD}/certs:/certs:ro `
  dtsms-test-client `
  /upload/test.txt `
  --host localhost `
  --port 8888 `
  --client-cert /certs/client.crt `
  --client-key /certs/client.key `
  --ca-cert /certs/ca.crt

# 使用 mTLS (推薦) - 一行版本 (需要加引號)
docker run --rm --network host -v "${PWD}/upload:/upload" -v "${PWD}/certs:/certs:ro" dtsms-test-client /upload/test.txt --host localhost --port 8888 --client-cert /certs/client.crt --client-key /certs/client.key --ca-cert /certs/ca.crt
```

**Note**:
- 使用 `localhost` 而不是 `127.0.0.1` (證書 CN 匹配)
- PowerShell 使用 `` ` `` (backtick) 換行,Bash 使用 `\`
- PowerShell 使用 `${PWD}`,Bash 使用 `$(pwd)`

## 參數說明

| 參數 | 說明 | 預設值 |
|------|------|--------|
| `file` | 要上傳的檔案路徑 (必填) | - |
| `--host` | 伺服器主機 | `127.0.0.1` |
| `--port` | 伺服器端口 | `8888` |
| `--secret` | HMAC 密鑰 | `supersecretkey` |
| `--no-tls` | 停用 TLS | 預設啟用 |
| `--client-cert` | 客戶端證書 (mTLS) | - |
| `--client-key` | 客戶端金鑰 (mTLS) | - |
| `--ca-cert` | CA 證書 | - |

## 網路配置注意事項

### Windows / macOS
- 使用 `network_mode: host` 時,`--host 127.0.0.1` 即可連接到本機伺服器
- 或使用 `host.docker.internal` 作為主機名稱

### Linux
- `network_mode: host` 讓容器使用主機網路
- 或使用 `172.17.0.1` (Docker bridge 網關) 連接到主機

## 測試範例

### 測試 1: 上傳小檔案
```bash
echo "Test message" > upload/small.txt
docker-compose run --rm test-client /upload/small.txt
```

### 測試 2: 上傳大檔案
```bash
# 創建 100MB 測試檔案
dd if=/dev/zero of=upload/large.bin bs=1M count=100
docker-compose run --rm test-client /upload/large.bin
```

### 測試 3: 錯誤的 HMAC 密鑰
```bash
docker-compose run --rm test-client \
  /upload/test.txt \
  --secret wrongsecret
```

## 故障排除

1. **連接被拒絕**
   - 確認伺服器正在運行: `docker ps | grep dtsms-webserver`
   - 檢查端口映射: `docker port dtsms-webserver`

2. **SSL 錯誤**
   - 確認伺服器是否要求 mTLS
   - 檢查證書路徑是否正確
   - 使用 `--no-tls` 測試不加密連接

3. **檔案未找到**
   - 確認檔案在 `upload/` 目錄中
   - 檢查路徑是否以 `/upload/` 開頭

## 清理

```bash
# 停止並刪除容器
docker-compose down

# 刪除映像
docker rmi dtsms-test-client
```
