from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import requests
import time
import os


def retrieve_scan_results(**context):
    """
    通過 data_id 獲取文件掃描或消毒結果

    API: GET /file/{data_id}
    功能: 查詢文件處理狀態和結果，支持輪詢直到處理完成
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
        raise ValueError("未提供 data_id，無法獲取結果")

    # API 端點
    url = f"{OPSWAT_API_URL}/file/{data_id}"

    # 請求標頭
    headers = {
        'apikey': OPSWAT_API_KEY,
    }

    # 輪詢配置
    max_retries = context.get('params', {}).get('max_retries', 30)  # 最多重試次數
    retry_interval = context.get('params', {}).get('retry_interval', 10)  # 重試間隔（秒）

    try:
        for attempt in range(max_retries):
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            result = response.json()

            # 檢查處理進度
            progress_percentage = result.get('progress_percentage', 0)
            scan_result_i = result.get('scan_results', {}).get('scan_all_result_i', 0)

            print(f"處理進度: {progress_percentage}%")

            # 判斷是否完成
            # progress_percentage = 100 表示完成
            # scan_all_result_i: 0=無威脅, 1=已感染, 2=可疑, 254=處理中, 255=未掃描
            if progress_percentage == 100:
                print(f"文件處理完成")

                # 解析掃描結果
                scan_details = result.get('scan_results', {}).get('scan_details', {})
                total_avs = result.get('scan_results', {}).get('total_avs', 0)
                total_detected_avs = result.get('scan_results', {}).get('total_detected_avs', 0)

                print(f"掃描引擎總數: {total_avs}")
                print(f"檢測到威脅的引擎數: {total_detected_avs}")
                print(f"掃描結果: {scan_result_i} (0=無威脅, 1=已感染, 2=可疑)")

                # 推送結果到 XCom
                context['ti'].xcom_push(key='final_result', value=result)
                context['ti'].xcom_push(key='scan_result_i', value=scan_result_i)
                context['ti'].xcom_push(key='is_infected', value=scan_result_i > 0)
                context['ti'].xcom_push(key='total_detected_avs', value=total_detected_avs)

                return result

            else:
                print(f"文件處理中，等待 {retry_interval} 秒後重試... (嘗試 {attempt + 1}/{max_retries})")
                time.sleep(retry_interval)

        # 如果達到最大重試次數仍未完成
        raise TimeoutError(f"文件處理超時，已重試 {max_retries} 次")

    except requests.exceptions.RequestException as e:
        print(f"獲取結果失敗: {str(e)}")
        raise


with DAG(
    dag_id='dag_opswat_retrieve_results',
    description='獲取 MetaDefender Core 文件處理結果（掃描或消毒）',
    start_date=datetime(2025, 12, 29),
    schedule_interval=None,
    catchup=False,
    tags=['opswat', 'retrieve-results', 'security'],
    params={
        'data_id': None,  # 從上游任務獲取或直接提供
        'max_retries': 30,  # 最多重試 30 次
        'retry_interval': 10,  # 每次重試間隔 10 秒
    }
) as dag:

    task_retrieve_results = PythonOperator(
        task_id='retrieve_results_task',
        python_callable=retrieve_scan_results,
        provide_context=True,
    )
