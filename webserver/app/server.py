import uvloop
import asyncio
from minio import Minio
import io
import uuid

minio_client = Minio(
    "minio:9000",
    access_key="minio",
    secret_key="minio123",
    secure=False
)

CHUNK_SIZE = 10 * 1024  # 10KB

async def handle_client(reader, writer):
    addr = writer.get_extra_info("peername")
    print(f"Connected from {addr}")

    file_id = uuid.uuid4().hex
    chunk_index = 0

    try:
        while True:
            data = await reader.read(CHUNK_SIZE)
            if not data:
                break
            object_name = f"{file_id}/chunk_{chunk_index:06d}"
            minio_client.put_object(
                "incoming",
                object_name,
                io.BytesIO(data),
                length=len(data)
            )
            print(f"Uploaded {object_name}, size={len(data)}")
            chunk_index += 1
    finally:
        writer.close()
        await writer.wait_closed()
        print(f"Upload finished for file_id={file_id}")

async def main():
    server = await asyncio.start_server(handle_client, "0.0.0.0", 8888)
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    uvloop.run(main())
