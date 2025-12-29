from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import requests
import os


def download_sanitized_file(**context):
    """
    下載經過 Deep CDR 處理後的清理文件

    API: GET /file/converted/{data_id}
    功能: 下載已消毒的安全文件
    """
    # MetaDefender Core API 配置
    OPSWAT_API_URL = os.getenv('OPSWAT_API_URL', 'https://your-metadefender-core-url')
    OPSWAT_API_KEY = os.getenv('OPSWAT_API_KEY', 'your-api-key')

    # 獲取 data_id (可以從上游任務的 XCom 獲取或直接傳入)
    data_id = context.get('params', {}).get('data_id')
    if not data_id:
        # 嘗試從 XCom 獲取
        data_id = context['ti'].xcom_pull(key='data_id')

    if not data_id:
        raise ValueError("未提供 data_id，無法下載文件")

    # 輸出路徑
    output_dir = context.get('params', {}).get('output_dir', '/tmp/sanitized')
    output_filename = context.get('params', {}).get('output_filename', 'sanitized_file')

    # 確保輸出目錄存在
    os.makedirs(output_dir, exist_ok=True)

    # API 端點
    url = f"{OPSWAT_API_URL}/file/converted/{data_id}"

    # 請求標頭
    headers = {
        'apikey': OPSWAT_API_KEY,
    }

    try:
        # 下載清理後的文件
        response = requests.get(url, headers=headers, stream=True, timeout=300)
        response.raise_for_status()

        # 從響應頭獲取文件名（如果有）
        content_disposition = response.headers.get('Content-Disposition', '')
        if 'filename=' in content_disposition:
            filename = content_disposition.split('filename=')[1].strip('"')
        else:
            # 從 Content-Type 推斷副檔名
            content_type = response.headers.get('Content-Type', 'application/octet-stream')
            extension = content_type.split('/')[-1] if '/' in content_type else 'bin'
            filename = f"{output_filename}.{extension}"

        # 完整輸出路徑
        output_path = os.path.join(output_dir, filename)

        # 寫入文件
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        print(f"清理後的文件已下載至: {output_path}")

        # 獲取文件大小
        file_size = os.path.getsize(output_path)
        print(f"文件大小: {file_size} bytes")

        # 推送結果到 XCom
        context['ti'].xcom_push(key='sanitized_file_path', value=output_path)
        context['ti'].xcom_push(key='sanitized_file_size', value=file_size)
        context['ti'].xcom_push(key='sanitized_filename', value=filename)

        return output_path

    except requests.exceptions.RequestException as e:
        print(f"下載清理文件失敗: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"HTTP 狀態碼: {e.response.status_code}")
            print(f"響應內容: {e.response.text}")
        raise
    except IOError as e:
        print(f"寫入文件失敗: {str(e)}")
        raise


with DAG(
    dag_id='dag_opswat_download_sanitized',
    description='下載 MetaDefender Core Deep CDR 處理後的清理文件',
    start_date=datetime(2025, 12, 29),
    schedule_interval=None,
    catchup=False,
    tags=['opswat', 'download', 'sanitized', 'cdr'],
    params={
        'data_id': None,  # 從上游任務獲取或直接提供
        'output_dir': '/tmp/sanitized',  # 輸出目錄
        'output_filename': 'sanitized_file',  # 輸出文件名（不含副檔名）
    }
) as dag:

    task_download_sanitized = PythonOperator(
        task_id='download_sanitized_task',
        python_callable=download_sanitized_file,
        provide_context=True,
    )
