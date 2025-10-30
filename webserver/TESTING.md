# TCP Server 測試指南

本文檔說明如何從 Docker 容器外測試 TCP 檔案上傳伺服器。

## 前置條件

1. **確保伺服器正在運行**
   ```bash
   cd webserver
   docker-compose up -d
   ```

2. **檢查伺服器狀態**
   ```bash
   docker-compose logs -f tcp_server
   ```
   應該看到類似：`Server running on 0.0.0.0:8888 (mTLS enabled)`

## 測試場景

### 場景 1: 無 TLS 測試（開發環境）

如果您在開發環境中關閉了 TLS：

```bash
# 在 .env 中設定
TLS_ENABLE=false

# 重啟伺服器
docker-compose restart

# 從 Docker 外測試
python app/test-client.py myfile.txt --no-tls
```

### 場景 2: TLS 測試（不驗證伺服器證書）

適用於自簽證書的測試環境：

```bash
python app/test-client.py myfile.txt
```

**注意**：此模式會跳過伺服器證書驗證（不建議用於生產環境）

### 場景 3: 完整 mTLS 測試（生產環境）

需要客戶端證書：

```bash
python app/test-client.py myfile.txt \
  --client-cert ./certs/client.crt \
  --client-key ./certs/client.key \
  --ca-cert ./certs/ca.crt
```

## 命令列參數說明

```bash
python app/test-client.py <file> [options]
```

**必需參數：**
- `file`: 要上傳的檔案路徑

**可選參數：**
- `--host`: 伺服器主機 (預設: `127.0.0.1`)
- `--port`: 伺服器端口 (預設: `8888`)
- `--secret`: HMAC 密鑰 (必須與伺服器的 `HMAC_SECRET` 一致)
- `--no-tls`: 停用 TLS
- `--client-cert`: 客戶端證書路徑 (mTLS)
- `--client-key`: 客戶端私鑰路徑 (mTLS)
- `--ca-cert`: CA 證書路徑（用於驗證伺服器）

## 測試範例

### 1. 上傳小檔案
```bash
echo "Hello World" > test.txt
python app/test-client.py test.txt
```

### 2. 上傳大檔案
```bash
dd if=/dev/zero of=largefile.bin bs=1M count=100  # 創建 100MB 檔案
python app/test-client.py largefile.bin
```

### 3. 測試 HMAC 驗證失敗
```bash
# 使用錯誤的密鑰
python app/test-client.py test.txt --secret wrongsecret
```
預期結果：`❌ Server rejected: ERR_AUTH`

### 4. 連接到遠端伺服器
```bash
python app/test-client.py myfile.txt \
  --host 192.168.1.100 \
  --port 8888 \
  --secret your_production_secret \
  --client-cert ./client.crt \
  --client-key ./client.key \
  --ca-cert ./ca.crt
```

## 生成測試證書

如果您需要生成自簽名證書進行測試：

### 1. 生成 CA 證書
```bash
openssl genrsa -out certs/ca.key 4096
openssl req -new -x509 -days 365 -key certs/ca.key -out certs/ca.crt \
  -subj "/CN=Test CA"
```

### 2. 生成伺服器證書
```bash
openssl genrsa -out certs/server.key 2048
openssl req -new -key certs/server.key -out certs/server.csr \
  -subj "/CN=localhost"
openssl x509 -req -in certs/server.csr -CA certs/ca.crt -CAkey certs/ca.key \
  -CAcreateserial -out certs/server.crt -days 365
```

### 3. 生成客戶端證書
```bash
openssl genrsa -out certs/client.key 2048
openssl req -new -key certs/client.key -out certs/client.csr \
  -subj "/CN=test-client"
openssl x509 -req -in certs/client.csr -CA certs/ca.crt -CAkey certs/ca.key \
  -CAcreateserial -out certs/client.crt -days 365
```

## 驗證上傳結果

### 檢查 MinIO 中的檔案

1. **訪問 MinIO Web UI**
   ```
   http://localhost:9001
   ```

2. **使用 MinIO Client (mc)**
   ```bash
   mc alias set myminio http://localhost:9000 minio minio123
   mc ls myminio/incoming
   ```

3. **查看合併後的檔案**
   ```bash
   mc ls myminio/incoming --recursive | grep merged
   ```

## 故障排除

### 問題 1: Connection refused
**原因**：伺服器未運行或端口未正確映射
**解決**：
```bash
docker-compose ps  # 確認容器運行
docker-compose logs tcp_server  # 查看日誌
```

### 問題 2: SSL Error
**原因**：伺服器要求 mTLS 但客戶端未提供證書
**解決**：使用 `--client-cert` 和 `--client-key` 參數

### 問題 3: ERR_AUTH
**原因**：HMAC 驗證失敗
**解決**：確保 `--secret` 參數與伺服器的 `HMAC_SECRET` 一致

### 問題 4: Timestamp 錯誤
**原因**：客戶端與伺服器時間差超過 5 分鐘
**解決**：同步系統時間
```bash
# Linux/Mac
sudo ntpdate -s time.nist.gov

# Windows
w32tm /resync
```

## 效能測試

### 上傳速度測試
```bash
# 創建 1GB 測試檔案
dd if=/dev/zero of=testfile.bin bs=1M count=1024

# 測試上傳時間
time python app/test-client.py testfile.bin
```

### 並發測試
```bash
# 同時上傳多個檔案
for i in {1..10}; do
  python app/test-client.py test$i.txt &
done
wait
```

## 安全注意事項

1. **生產環境必須啟用 TLS**
   - 設定 `TLS_ENABLE=true`
   - 使用有效的 CA 簽發證書

2. **使用強 HMAC 密鑰**
   ```bash
   # 生成隨機密鑰
   openssl rand -base64 32
   ```

3. **限制網路訪問**
   - 使用防火牆限制只有授權 IP 可訪問
   - 考慮使用 VPN 或專用網路

4. **監控與日誌**
   ```bash
   # 持續監控伺服器日誌
   docker-compose logs -f tcp_server
   ```
