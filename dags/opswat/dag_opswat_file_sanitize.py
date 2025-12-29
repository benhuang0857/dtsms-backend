from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import requests
import os


def sanitize_file_with_opswat(**context):
    """
    上傳文件到 MetaDefender Core 進行 Deep CDR (內容消毒與重建)

    API: POST /file
    功能: 使用 Deep CDR 技術清除文件中的潛在威脅，返回安全的文件
    Workflow: sanitize
    """
    # MetaDefender Core API 配置
    OPSWAT_API_URL = os.getenv('OPSWAT_API_URL', 'https://your-metadefender-core-url')
    OPSWAT_API_KEY = os.getenv('OPSWAT_API_KEY', 'your-api-key')

    # 文件路徑
    file_path = context.get('params', {}).get('file_path', '/tmp/test_file.txt')

    # API 端點
    url = f"{OPSWAT_API_URL}/file"

    # 請求標頭
    headers = {
        'apikey': OPSWAT_API_KEY,
    }

    # 參數設置 - 使用 sanitize 工作流
    params = {
        'workflow': 'sanitize',  # 指定為消毒工作流
        'archivepwd': context.get('params', {}).get('archive_password', ''),
        'userAgent': context.get('params', {}).get('user_agent', 'DTSMS-Backend/1.0'),
    }

    # CDR 配置選項
    cdr_options = context.get('params', {}).get('cdr_options', {})
    if cdr_options:
        # 可以添加額外的 CDR 選項
        # 例如: 'removeAttachments': '1', 'removeMacros': '1'
        params.update(cdr_options)

    try:
        # 讀取並上傳文件進行消毒
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

        # 返回 data_id 用於後續下載清理後的文件
        data_id = result.get('data_id')
        print(f"文件已提交消毒處理，data_id: {data_id}")

        # 推送到 XCom 供後續任務使用
        context['ti'].xcom_push(key='data_id', value=data_id)
        context['ti'].xcom_push(key='sanitize_result', value=result)
        context['ti'].xcom_push(key='original_file_path', value=file_path)

        return data_id

    except requests.exceptions.RequestException as e:
        print(f"文件消毒失敗: {str(e)}")
        raise
    except FileNotFoundError:
        print(f"找不到文件: {file_path}")
        raise


with DAG(
    dag_id='dag_opswat_file_sanitize',
    description='使用 MetaDefender Core Deep CDR 技術清除文件中的威脅',
    start_date=datetime(2025, 12, 29),
    schedule_interval=None,
    catchup=False,
    tags=['opswat', 'sanitize', 'cdr', 'security'],
    params={
        'file_path': '/tmp/test_file.txt',
        'archive_password': '',
        'user_agent': 'DTSMS-Backend/1.0',
        'cdr_options': {
            # 可選的 CDR 配置
            # 'removeAttachments': '1',  # 移除附件
            # 'removeMacros': '1',        # 移除宏
            # 'removeExternalLinks': '1', # 移除外部連結
        },
    }
) as dag:

    task_sanitize_file = PythonOperator(
        task_id='sanitize_file_task',
        python_callable=sanitize_file_with_opswat,
        provide_context=True,
    )
