# MinIO Docker Setup

Simple setup for MinIO, MinIO Console (built-in), and MinIO Client using Docker Compose.

## Requirements

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/)

## Quick Start

### Option 1: Using the start script (Recommended)

```bash
cd minio
./start.sh
```

The script will:
- Load configuration from `.env` file
- Create necessary directories
- Start MinIO services
- Create additional console user (optional)

### Option 2: Manual start

1. **Configure environment** (optional, defaults are provided):
   Edit `.env` file to customize:
   ```env
   MINIO_PORT=9001
   MINIO_CONSOLE_PORT=9091
   MINIO_ROOT_USER=minio
   MINIO_ROOT_PASSWORD=minio123
   ```

2. **Start services**:
   ```bash
   cd minio
   docker-compose up -d
   ```

## Access

After starting the services:

- **MinIO API**: http://localhost:9001
- **MinIO Console**: http://localhost:9091
  - Username: `minio`
  - Password: `minio123`

## Using MinIO Client (mc)

The `minio-client` container provides the `mc` CLI tool for administrating MinIO:

```bash
# Create an alias for easier access
alias mc='docker exec -it minio-client mc'

# Example: Create a bucket
mc mb minio/mybucket

# Example: List buckets
mc ls minio/

# Example: Upload a file
mc cp myfile.txt minio/mybucket/
```

For more commands, refer to [MinIO Client documentation](https://min.io/docs/minio/linux/reference/minio-mc.html).

## Configuration

All configuration is stored in the `.env` file:

- `MINIO_STORAGE_LOCATION`: Data persistence location (default: `./data`)
- `MINIO_PORT`: MinIO API port (default: `9001`)
- `MINIO_CONSOLE_PORT`: MinIO Console port (default: `9091`)
- `MINIO_ROOT_USER`: Root username (default: `minio`)
- `MINIO_ROOT_PASSWORD`: Root password (default: `minio123`)

## Services

- **minio**: MinIO object storage server with built-in console
- **minio-client**: MinIO client (mc) for CLI operations

## Stopping Services

```bash
docker-compose down
```

To remove all data:
```bash
docker-compose down -v
```

## Integration with Airflow

To use this MinIO instance with Airflow (running separately):

1. Ensure both services can communicate (same Docker network or use host networking)
2. In Airflow, create a connection:
   - Connection ID: `minio_local`
   - Connection Type: `Amazon Web Services`
   - Extra: `{"endpoint_url": "http://minio:9000", "aws_access_key_id": "minio", "aws_secret_access_key": "minio123"}`

   Note: If Airflow is not in the same Docker network, use `http://localhost:9001` instead of `http://minio:9000`.