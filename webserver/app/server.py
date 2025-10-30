import os
import io
import ssl
import json
import time
import uuid
import hmac
import hashlib
import asyncio
import logging
from pathlib import Path
from functools import partial
from concurrent.futures import ThreadPoolExecutor
from minio import Minio
from minio.error import S3Error
import uvloop

# ------------------ 設定 ------------------
HOST = "0.0.0.0"
PORT = int(os.getenv("TCP_PORT", "8888"))

MINIO_HOST = os.getenv("MINIO_HOST", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minio")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minio123")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "incoming")

HMAC_SECRET = os.getenv("HMAC_SECRET", "supersecretkey").encode()
TOKEN_WINDOW = 300  # 秒

CHUNK_SIZE = 64 * 1024  # 64KB
THREAD_POOL = 8
UPLOAD_RETRIES = 3
READ_TIMEOUT = 30.0

TLS_ENABLE = os.getenv("TLS_ENABLE", "true").lower() == "true"
TLS_CERT = os.getenv("TLS_CERT", "/certs/server.crt")
TLS_KEY = os.getenv("TLS_KEY", "/certs/server.key")
TLS_CA = os.getenv("TLS_CA", "/certs/ca.crt")  # 用於驗證 client

# ------------------ 初始化 ------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("SecureTCPServer")

minio_client = Minio(
    MINIO_HOST,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)

try:
    if not minio_client.bucket_exists(MINIO_BUCKET):
        minio_client.make_bucket(MINIO_BUCKET)
except Exception as e:
    log.warning("Bucket init failed: %s", e)

# ------------------ 驗證 ------------------
def verify_hmac(header: dict) -> bool:
    timestamp = str(header["timestamp"])
    if abs(time.time() - int(timestamp)) > TOKEN_WINDOW:
        return False
    msg = f"{header['filename']}:{header['size']}:{timestamp}".encode()
    expected = hmac.new(HMAC_SECRET, msg, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header["hmac"])

# ------------------ MinIO 上傳 ------------------
def blocking_put(bucket: str, object_name: str, data: bytes):
    for attempt in range(1, UPLOAD_RETRIES + 1):
        try:
            minio_client.put_object(bucket, object_name, io.BytesIO(data), len(data))
            return
        except Exception as e:
            log.warning("Upload attempt %d failed: %s", attempt, e)
            time.sleep(attempt * 0.5)
    raise RuntimeError(f"Upload failed: {object_name}")

# ------------------ 檔案合併 ------------------
def merge_chunks(bucket: str, file_id: str, total_chunks: int, final_name: str):
    tmpfile = Path(f"/tmp/{file_id}.bin")
    with tmpfile.open("wb") as out:
        for i in range(total_chunks):
            chunk_name = f"{file_id}/chunk_{i:06d}"
            response = minio_client.get_object(bucket, chunk_name)
            out.write(response.read())
            response.close()
            response.release_conn()

    # 重新上傳合併後檔案
    file_hash = hashlib.sha256(tmpfile.read_bytes()).hexdigest()
    meta = {"sha256": file_hash, "original_name": final_name}
    with tmpfile.open("rb") as f:
        minio_client.put_object(bucket, f"{file_id}/merged/{final_name}", f, tmpfile.stat().st_size, metadata=meta)

    # 清理 chunks
    for i in range(total_chunks):
        try:
            minio_client.remove_object(bucket, f"{file_id}/chunk_{i:06d}")
        except Exception as e:
            log.warning(f"Failed to remove chunk {i}: {e}")

    tmpfile.unlink(missing_ok=True)
    return file_hash

# ------------------ 處理 Client ------------------
async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, pool: ThreadPoolExecutor):
    peer = writer.get_extra_info("peername")
    cert = writer.get_extra_info("peercert")
    subject = cert.get("subject", [[""]])[0][0][1] if cert else "Unknown"
    log.info(f"Connected from {peer}, client_cert={subject}")

    # 1️⃣ 收到 header JSON
    try:
        header_line = await asyncio.wait_for(reader.readline(), timeout=5.0)
        header = json.loads(header_line.decode().strip())
    except Exception as e:
        log.error("Invalid header: %s", e)
        writer.close()
        await writer.wait_closed()
        return

    if not verify_hmac(header):
        writer.write(b"ERR_AUTH\n")
        await writer.drain()
        writer.close()
        await writer.wait_closed()
        log.warning("HMAC verify failed for %s", peer)
        return

    filename = header["filename"]
    filesize = header["size"]
    file_id = uuid.uuid4().hex
    chunk_index = 0
    total_read = 0

    writer.write(b"OK\n")
    await writer.drain()

    # 2️⃣ 接收檔案內容
    try:
        while True:
            chunk = await asyncio.wait_for(reader.read(CHUNK_SIZE), timeout=READ_TIMEOUT)
            if not chunk:
                break
            total_read += len(chunk)
            object_name = f"{file_id}/chunk_{chunk_index:06d}"
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(pool, partial(blocking_put, MINIO_BUCKET, object_name, chunk))
            chunk_index += 1
            log.info(f"Chunk {chunk_index} uploaded ({len(chunk)} bytes)")

        # 3️⃣ 上傳完畢 -> 合併
        if total_read == filesize:
            loop = asyncio.get_running_loop()
            file_hash = await loop.run_in_executor(pool, partial(merge_chunks, MINIO_BUCKET, file_id, chunk_index, filename))
            log.info(f"✅ File merged successfully: {filename} (SHA256={file_hash})")
            writer.write(b"UPLOAD_COMPLETE\n")
        else:
            log.warning("File size mismatch: expected %d, got %d", filesize, total_read)
            writer.write(b"ERR_SIZE_MISMATCH\n")

        await writer.drain()
    except Exception as e:
        log.error("Error while receiving: %s", e)
    finally:
        writer.close()
        await writer.wait_closed()
        log.info(f"Connection closed from {peer}")

# ------------------ 主程式 ------------------
async def main():
    pool = ThreadPoolExecutor(max_workers=THREAD_POOL)

    ssl_ctx = None
    if TLS_ENABLE:
        ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_ctx.load_cert_chain(TLS_CERT, TLS_KEY)
        ssl_ctx.load_verify_locations(TLS_CA)
        ssl_ctx.verify_mode = ssl.CERT_REQUIRED  # 啟用 mTLS

    server = await asyncio.start_server(lambda r, w: handle_client(r, w, pool), HOST, PORT, ssl=ssl_ctx)
    addr = ", ".join(str(s.getsockname()) for s in server.sockets)
    tls_status = "mTLS enabled" if TLS_ENABLE else "TLS disabled"
    log.info(f"Server running on {addr} ({tls_status})")

    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Server stopped.")
