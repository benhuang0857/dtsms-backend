# Airflow MinIO Upload DAG

This is an Apache Airflow DAG project for uploading local files to MinIO.

## Project Structure

```
airflow/
├── dags/
│   └── dag_upload_file_to_minio.py    # File upload DAG
├── docker-compose.yml                 # Docker services configuration
├── minio/                            # MinIO related configuration
└── README.md                         # Project documentation
```

## DAG Features

- **DAG ID**: `dag_upload_file_to_minio`
- **Function**: Upload local file `/tmp/file.txt` to MinIO `incoming` bucket
- **Trigger**: Manual trigger (no schedule)
- **Tags**: `minio`, `upload`

## Usage

1. Ensure MinIO service is running
2. Configure `minio_local` connection in Airflow
3. Prepare the file to upload at `/tmp/file.txt`
4. Manually trigger the DAG in Airflow UI

## Requirements

- Apache Airflow
- MinIO service
- Python packages:
  - `apache-airflow-providers-amazon`

## Configuration

Configure a connection named `minio_local` in Airflow with MinIO connection details.