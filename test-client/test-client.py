import os
import ssl
import json
import time
import hmac
import hashlib
import argparse
from pathlib import Path

# 預設配置
DEFAULT_HOST = "localhost"
DEFAULT_PORT = 8888
DEFAULT_HMAC_SECRET = "supersecretkey"
CHUNK_SIZE = 64 * 1024  # 64KB (與伺服器一致)

# 證書路徑 (相對於 test-client 目錄)
SCRIPT_DIR = Path(__file__).parent
DEFAULT_CLIENT_CERT = SCRIPT_DIR / "certs" / "client.crt"
DEFAULT_CLIENT_KEY = SCRIPT_DIR / "certs" / "client.key"
DEFAULT_CA_CERT = SCRIPT_DIR / "certs" / "ca.crt"

def calculate_hmac(filename: str, filesize: int, timestamp: int, secret: str) -> str:
    """計算 HMAC (與 server.py 一致的邏輯)"""
    msg = f"{filename}:{filesize}:{timestamp}".encode()
    return hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()

def send_file(
    file_path: str,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    hmac_secret: str = DEFAULT_HMAC_SECRET,
    use_tls: bool = True,
    client_cert: str = None,
    client_key: str = None,
    ca_cert: str = None
):
    """
    發送檔案到 TCP 伺服器

    Args:
        file_path: 要上傳的檔案路徑
        host: 伺服器主機
        port: 伺服器端口
        hmac_secret: HMAC 密鑰
        use_tls: 是否使用 TLS
        client_cert: 客戶端證書路徑 (mTLS)
        client_key: 客戶端金鑰路徑 (mTLS)
        ca_cert: CA 證書路徑
    """
    file_path = Path(file_path)
    if not file_path.exists():
        print(f"[ERROR] File not found: {file_path}")
        return False

    filename = file_path.name
    filesize = file_path.stat().st_size
    timestamp = int(time.time())

    # 計算 HMAC
    hmac_value = calculate_hmac(filename, filesize, timestamp, hmac_secret)

    # 構建 header
    header = {
        "filename": filename,
        "size": filesize,
        "timestamp": timestamp,
        "hmac": hmac_value
    }

    print(f"[UPLOAD] Sending file: {filename}")
    print(f"   Size: {filesize} bytes ({filesize / 1024 / 1024:.2f} MB)")
    print(f"   Server: {host}:{port}")
    print(f"   TLS: {'Enabled' if use_tls else 'Disabled'}")

    try:
        # 建立連接
        if use_tls:
            # 創建 SSL context
            ssl_ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)

            if ca_cert:
                ssl_ctx.load_verify_locations(ca_cert)
            else:
                # 如果沒有提供 CA，則不驗證伺服器證書（僅用於測試）
                ssl_ctx.check_hostname = False
                ssl_ctx.verify_mode = ssl.CERT_NONE

            # 如果有客戶端證書，加載它 (mTLS)
            if client_cert and client_key:
                ssl_ctx.load_cert_chain(client_cert, client_key)
                print(f"   mTLS: Enabled (cert: {client_cert})")

            # 建立 TLS 連接
            with ssl_ctx.wrap_socket(
                __import__('socket').socket(__import__('socket').AF_INET, __import__('socket').SOCK_STREAM),
                server_hostname=host
            ) as sock:
                sock.connect((host, port))
                return _send_file_through_socket(sock, file_path, header, filesize)
        else:
            # 普通 TCP 連接
            with __import__('socket').create_connection((host, port)) as sock:
                return _send_file_through_socket(sock, file_path, header, filesize)

    except ConnectionRefusedError:
        print(f"[ERROR] Connection refused. Is the server running on {host}:{port}?")
        return False
    except ssl.SSLError as e:
        print(f"[ERROR] SSL Error: {e}")
        print("   Hint: Check if server requires mTLS (client certificate)")
        return False
    except Exception as e:
        print(f"[ERROR] {e}")
        return False

def _send_file_through_socket(sock, file_path: Path, header: dict, filesize: int) -> bool:
    """透過 socket 發送檔案"""
    # 1. 發送 header
    header_json = json.dumps(header) + "\n"
    sock.sendall(header_json.encode())
    print(f"[OK] Header sent")

    # 2. 接收伺服器響應
    response = sock.recv(1024).decode().strip()
    if response != "OK":
        print(f"[ERROR] Server rejected: {response}")
        return False
    print(f"[OK] Server accepted, starting upload...")

    # 3. 發送檔案內容
    total_sent = 0
    with file_path.open("rb") as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            sock.sendall(chunk)
            total_sent += len(chunk)
            progress = (total_sent / filesize) * 100
            print(f"   Progress: {progress:.1f}% ({total_sent}/{filesize} bytes)", end="\r")

    print()  # 換行
    print(f"[OK] File data sent ({total_sent} bytes)")

    # 3.5. 關閉寫入端,通知伺服器數據發送完畢
    sock.shutdown(__import__('socket').SHUT_WR)

    # 4. 等待伺服器最終響應
    final_response = sock.recv(1024).decode().strip()
    if final_response == "UPLOAD_COMPLETE":
        print(f"[SUCCESS] Upload completed successfully!")
        return True
    else:
        print(f"[WARNING] Server response: {final_response}")
        return False

def main():
    parser = argparse.ArgumentParser(description="TCP File Upload Client (with HMAC & TLS)")
    parser.add_argument("file", help="File to upload")
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"Server host (default: {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Server port (default: {DEFAULT_PORT})")
    parser.add_argument("--secret", default=DEFAULT_HMAC_SECRET, help="HMAC secret key")
    parser.add_argument("--no-tls", action="store_true", help="Disable TLS")
    parser.add_argument("--client-cert", help=f"Client certificate for mTLS (default: {DEFAULT_CLIENT_CERT})")
    parser.add_argument("--client-key", help=f"Client key for mTLS (default: {DEFAULT_CLIENT_KEY})")
    parser.add_argument("--ca-cert", help=f"CA certificate to verify server (default: {DEFAULT_CA_CERT})")

    args = parser.parse_args()

    # 使用預設證書路徑 (如果存在且未指定)
    client_cert = args.client_cert or (str(DEFAULT_CLIENT_CERT) if DEFAULT_CLIENT_CERT.exists() else None)
    client_key = args.client_key or (str(DEFAULT_CLIENT_KEY) if DEFAULT_CLIENT_KEY.exists() else None)
    ca_cert = args.ca_cert or (str(DEFAULT_CA_CERT) if DEFAULT_CA_CERT.exists() else None)

    success = send_file(
        file_path=args.file,
        host=args.host,
        port=args.port,
        hmac_secret=args.secret,
        use_tls=not args.no_tls,
        client_cert=client_cert,
        client_key=client_key,
        ca_cert=ca_cert
    )

    exit(0 if success else 1)

if __name__ == "__main__":
    main()
