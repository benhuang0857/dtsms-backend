from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import requests
import hashlib
import os


def calculate_file_hash(file_path, algorithm='sha256'):
    """
    計算文件的哈希值

    Args:
        file_path: 文件路徑
        algorithm: 哈希算法 (md5, sha1, sha256)
    """
    hash_func = hashlib.new(algorithm)
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hash_func.update(chunk)
    return hash_func.hexdigest()


def lookup_hash_in_opswat(**context):
    """
    通過哈希值查詢文件是否已在 MetaDefender Core 中存在掃描結果

    API: GET /hash/{hash}
    功能: 查詢文件哈希值，如果已掃描過則直接返回結果，避免重複掃描
    """
    # MetaDefender Core API 配置
    OPSWAT_API_URL = os.getenv('OPSWAT_API_URL', 'https://your-metadefender-core-url')
    OPSWAT_API_KEY = os.getenv('OPSWAT_API_KEY', 'your-api-key')

    # 獲取參數
    file_path = context.get('params', {}).get('file_path', '/tmp/test_file.txt')
    hash_algorithm = context.get('params', {}).get('hash_algorithm', 'sha256')

    # 如果提供了哈希值則直接使用，否則計算文件哈希
    file_hash = context.get('params', {}).get('file_hash')
    if not file_hash:
        file_hash = calculate_file_hash(file_path, hash_algorithm)
        print(f"計算得到的 {hash_algorithm.upper()} 哈希值: {file_hash}")

    # API 端點
    url = f"{OPSWAT_API_URL}/hash/{file_hash}"

    # 請求標頭
    headers = {
        'apikey': OPSWAT_API_KEY,
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)

        if response.status_code == 200:
            result = response.json()
            print(f"找到哈希記錄，文件已存在於系統中")

            # 推送結果到 XCom
            context['ti'].xcom_push(key='hash_lookup_result', value=result)
            context['ti'].xcom_push(key='file_hash', value=file_hash)
            context['ti'].xcom_push(key='hash_found', value=True)

            return result

        elif response.status_code == 404:
            print(f"未找到哈希記錄，文件需要進行掃描")
            context['ti'].xcom_push(key='hash_found', value=False)
            context['ti'].xcom_push(key='file_hash', value=file_hash)
            return None

        else:
            response.raise_for_status()

    except requests.exceptions.RequestException as e:
        print(f"哈希查詢失敗: {str(e)}")
        raise


with DAG(
    dag_id='dag_opswat_hash_lookup',
    description='通過哈希值查詢文件在 MetaDefender Core 中的掃描記錄',
    start_date=datetime(2025, 12, 29),
    schedule_interval=None,
    catchup=False,
    tags=['opswat', 'hash-lookup', 'security'],
    params={
        'file_path': '/tmp/test_file.txt',
        'file_hash': None,  # 可選：直接提供哈希值
        'hash_algorithm': 'sha256',  # md5, sha1, sha256
    }
) as dag:

    task_lookup_hash = PythonOperator(
        task_id='lookup_hash_task',
        python_callable=lookup_hash_in_opswat,
        provide_context=True,
    )
