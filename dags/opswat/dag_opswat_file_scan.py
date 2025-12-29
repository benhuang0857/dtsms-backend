from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import requests
import os


def scan_file_with_opswat(**context):
    """
    上傳文件到 MetaDefender Core 進行掃描

    API: POST /file
    功能: 上傳文件並啟動多引擎掃描
    """
    # MetaDefender Core API 配置
    OPSWAT_API_URL = os.getenv('OPSWAT_API_URL', 'https://your-metadefender-core-url')
    OPSWAT_API_KEY = os.getenv('OPSWAT_API_KEY', 'your-api-key')

    # 文件路徑 (從 MinIO 或本地)
    file_path = context.get('params', {}).get('file_path', '/tmp/test_file.txt')

    # API 端點
    url = f"{OPSWAT_API_URL}/file"

    # 請求標頭
    headers = {
        'apikey': OPSWAT_API_KEY,
    }

    # 可選參數
    params = {
        'archivepwd': context.get('params', {}).get('archive_password', ''),  # 壓縮檔密碼
        'samplesharing': context.get('params', {}).get('sample_sharing', '0'),  # 樣本共享
        'dynamic': context.get('params', {}).get('dynamic_analysis', '0'),  # 動態分析
    }

    try:
        # 讀取並上傳文件
        with open(file_path, 'rb') as file:
            response = requests.post(
                url,
                headers=headers,
                params=params,
                files={'file': file},
                timeout=300
            )

        response.raise_for_status()
        result = response.json()

        # 返回 data_id 用於後續查詢結果
        data_id = result.get('data_id')
        print(f"文件已上傳成功，data_id: {data_id}")

        # 推送到 XCom 供後續任務使用
        context['ti'].xcom_push(key='data_id', value=data_id)
        context['ti'].xcom_push(key='scan_result', value=result)

        return data_id

    except requests.exceptions.RequestException as e:
        print(f"文件掃描失敗: {str(e)}")
        raise
    except FileNotFoundError:
        print(f"找不到文件: {file_path}")
        raise


with DAG(
    dag_id='dag_opswat_file_scan',
    description='上傳文件到 MetaDefender Core 進行多引擎掃描',
    start_date=datetime(2025, 12, 29),
    schedule_interval=None,  # 手動觸發或由其他 DAG 觸發
    catchup=False,
    tags=['opswat', 'file-scan', 'security'],
    params={
        'file_path': '/tmp/test_file.txt',
        'archive_password': '',
        'sample_sharing': '0',
        'dynamic_analysis': '0',
    }
) as dag:

    task_scan_file = PythonOperator(
        task_id='scan_file_task',
        python_callable=scan_file_with_opswat,
        provide_context=True,
    )
