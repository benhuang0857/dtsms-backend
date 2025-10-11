from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from datetime import datetime

def upload_file_to_minio():
    """
    將本地檔案 /tmp/file.txt 上傳到 MinIO 的 incoming bucket
    """
    s3 = S3Hook(aws_conn_id='minio_local')
    s3.load_file(
        filename='/tmp/file.txt',
        key='file.txt',
        bucket_name='incoming',
        replace=True
    )

with DAG(
    dag_id='dag_upload_file_to_minio',  # 正式 DAG 名稱
    description='DAG 將本地檔案上傳到 MinIO bucket',
    start_date=datetime(2025, 10, 12),
    schedule_interval=None,
    catchup=False,
    tags=['minio', 'upload']
) as dag:

    task_upload_file = PythonOperator(
        task_id='upload_file_task',
        python_callable=upload_file_to_minio
    )
