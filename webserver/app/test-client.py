import socket
import os

CHUNK_SIZE = 10 * 1024  # 10KB

def send_file(file_path, host="127.0.0.1", port=8888):
    filesize = os.path.getsize(file_path)
    print(f"Sending {file_path} ({filesize} bytes)")

    with socket.create_connection((host, port)) as sock:
        with open(file_path, "rb") as f:
            while True:
                data = f.read(CHUNK_SIZE)
                if not data:
                    break
                sock.sendall(data)
    print("File sent successfully")

if __name__ == "__main__":
    send_file("testfile.txt")  # 換成你要測的檔案
