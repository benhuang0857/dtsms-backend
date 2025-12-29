from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.dummy import DummyOperator
from datetime import datetime
import requests
import hashlib
import os


def calculate_hash_and_lookup(**context):
    """步驟 1: 計算文件哈希並查詢是否已存在掃描記錄"""
    OPSWAT_API_URL = os.getenv('OPSWAT_API_URL', 'https://your-metadefender-core-url')
    OPSWAT_API_KEY = os.getenv('OPSWAT_API_KEY', 'your-api-key')

    file_path = context.get('params', {}).get('file_path', '/tmp/test_file.txt')

    # 計算 SHA256 哈希
    hash_func = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hash_func.update(chunk)
    file_hash = hash_func.hexdigest()

    print(f"文件哈希: {file_hash}")

    # 查詢哈希
    url = f"{OPSWAT_API_URL}/hash/{file_hash}"
    headers = {'apikey': OPSWAT_API_KEY}

    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            result = response.json()
            context['ti'].xcom_push(key='hash_found', value=True)
            context['ti'].xcom_push(key='hash_result', value=result)
            return 'hash_found'
        else:
            context['ti'].xcom_push(key='hash_found', value=False)
            context['ti'].xcom_push(key='file_path', value=file_path)
            return 'hash_not_found'
    except Exception as e:
        print(f"哈希查詢失敗: {e}")
        return 'hash_not_found'


def decide_next_step(**context):
    """步驟 2: 根據哈希查詢結果決定下一步"""
    hash_found = context['ti'].xcom_pull(key='hash_found')

    if hash_found:
        print("文件已在系統中，直接返回結果")
        return 'report_existing_result'
    else:
        print("文件未在系統中，需要進行掃描")
        return 'upload_and_scan'


def upload_and_scan(**context):
    """步驟 3: 上傳文件並進行掃描"""
    OPSWAT_API_URL = os.getenv('OPSWAT_API_URL', 'https://your-metadefender-core-url')
    OPSWAT_API_KEY = os.getenv('OPSWAT_API_KEY', 'your-api-key')

    file_path = context['ti'].xcom_pull(key='file_path')
    if not file_path:
        file_path = context.get('params', {}).get('file_path', '/tmp/test_file.txt')

    workflow = context.get('params', {}).get('workflow', 'multiscan')  # multiscan 或 sanitize

    url = f"{OPSWAT_API_URL}/file"
    headers = {'apikey': OPSWAT_API_KEY}
    params = {'workflow': workflow}

    with open(file_path, 'rb') as file:
        response = requests.post(url, headers=headers, params=params, files={'file': file}, timeout=300)

    response.raise_for_status()
    result = response.json()
    data_id = result.get('data_id')

    print(f"文件已上傳，data_id: {data_id}")
    context['ti'].xcom_push(key='data_id', value=data_id)
    context['ti'].xcom_push(key='workflow', value=workflow)

    return data_id


def poll_results(**context):
    """步驟 4: 輪詢獲取處理結果"""
    import time

    OPSWAT_API_URL = os.getenv('OPSWAT_API_URL', 'https://your-metadefender-core-url')
    OPSWAT_API_KEY = os.getenv('OPSWAT_API_KEY', 'your-api-key')

    data_id = context['ti'].xcom_pull(key='data_id')
    url = f"{OPSWAT_API_URL}/file/{data_id}"
    headers = {'apikey': OPSWAT_API_KEY}

    max_retries = 30
    retry_interval = 10

    for attempt in range(max_retries):
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        result = response.json()

        progress = result.get('progress_percentage', 0)
        print(f"處理進度: {progress}%")

        if progress == 100:
            print("處理完成")
            context['ti'].xcom_push(key='final_result', value=result)

            # 解析結果
            scan_result = result.get('scan_results', {})
            scan_all_result_i = scan_result.get('scan_all_result_i', 0)
            total_detected_avs = scan_result.get('total_detected_avs', 0)

            context['ti'].xcom_push(key='scan_result_i', value=scan_all_result_i)
            context['ti'].xcom_push(key='is_infected', value=scan_all_result_i > 0)
            context['ti'].xcom_push(key='total_detected_avs', value=total_detected_avs)

            return result

        time.sleep(retry_interval)

    raise TimeoutError("處理超時")


def decide_action_based_on_result(**context):
    """步驟 5: 根據掃描結果決定後續動作"""
    workflow = context['ti'].xcom_pull(key='workflow')
    scan_result_i = context['ti'].xcom_pull(key='scan_result_i')

    if workflow == 'sanitize':
        # 如果是消毒流程，直接下載清理後的文件
        return 'download_sanitized_file'
    elif scan_result_i == 0:
        # 如果掃描結果為無威脅
        print("文件安全，無威脅")
        return 'report_clean'
    else:
        # 如果檢測到威脅
        print(f"檢測到威脅，掃描結果: {scan_result_i}")
        return 'report_threat_detected'


def download_sanitized(**context):
    """步驟 6: 下載清理後的文件（僅在 sanitize 工作流中）"""
    OPSWAT_API_URL = os.getenv('OPSWAT_API_URL', 'https://your-metadefender-core-url')
    OPSWAT_API_KEY = os.getenv('OPSWAT_API_KEY', 'your-api-key')

    data_id = context['ti'].xcom_pull(key='data_id')
    url = f"{OPSWAT_API_URL}/file/converted/{data_id}"
    headers = {'apikey': OPSWAT_API_KEY}

    output_dir = '/tmp/sanitized'
    os.makedirs(output_dir, exist_ok=True)

    response = requests.get(url, headers=headers, stream=True, timeout=300)
    response.raise_for_status()

    output_path = os.path.join(output_dir, f'sanitized_{data_id}.bin')
    with open(output_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    print(f"清理後的文件已保存至: {output_path}")
    context['ti'].xcom_push(key='sanitized_file_path', value=output_path)

    return output_path


def report_result(**context):
    """最終報告"""
    task_instance = context['ti']

    print("="*50)
    print("MetaDefender Core 處理結果報告")
    print("="*50)

    # 檢查是否使用了現有哈希結果
    hash_found = task_instance.xcom_pull(key='hash_found')
    if hash_found:
        print("使用了現有的掃描記錄（哈希匹配）")
        hash_result = task_instance.xcom_pull(key='hash_result')
        print(f"哈希結果: {hash_result}")
    else:
        print("執行了新的文件掃描")

        data_id = task_instance.xcom_pull(key='data_id')
        workflow = task_instance.xcom_pull(key='workflow')
        scan_result_i = task_instance.xcom_pull(key='scan_result_i')
        total_detected_avs = task_instance.xcom_pull(key='total_detected_avs')

        print(f"Data ID: {data_id}")
        print(f"工作流: {workflow}")
        print(f"掃描結果: {scan_result_i} (0=無威脅, 1=已感染, 2=可疑)")
        print(f"檢測到威脅的引擎數: {total_detected_avs}")

        if workflow == 'sanitize':
            sanitized_path = task_instance.xcom_pull(key='sanitized_file_path')
            if sanitized_path:
                print(f"清理後的文件路徑: {sanitized_path}")

    print("="*50)


with DAG(
    dag_id='dag_opswat_complete_workflow',
    description='MetaDefender Core 完整工作流：哈希查詢 → 掃描/消毒 → 結果處理',
    start_date=datetime(2025, 12, 29),
    schedule_interval=None,
    catchup=False,
    tags=['opswat', 'complete-workflow', 'security'],
    params={
        'file_path': '/tmp/test_file.txt',
        'workflow': 'multiscan',  # 'multiscan' 或 'sanitize'
    }
) as dag:

    start = DummyOperator(task_id='start')

    # 步驟 1: 哈希查詢
    task_hash_lookup = PythonOperator(
        task_id='hash_lookup_and_decide',
        python_callable=calculate_hash_and_lookup,
        provide_context=True,
    )

    # 步驟 2: 分支 - 根據哈希查詢結果決定
    task_branch = BranchPythonOperator(
        task_id='decide_next_step',
        python_callable=decide_next_step,
        provide_context=True,
    )

    # 步驟 3a: 如果找到哈希，直接報告
    task_report_existing = DummyOperator(task_id='report_existing_result')

    # 步驟 3b: 如果未找到，上傳並掃描
    task_upload = PythonOperator(
        task_id='upload_and_scan',
        python_callable=upload_and_scan,
        provide_context=True,
    )

    # 步驟 4: 輪詢結果
    task_poll = PythonOperator(
        task_id='poll_results',
        python_callable=poll_results,
        provide_context=True,
        trigger_rule='none_failed',
    )

    # 步驟 5: 根據結果決定動作
    task_decide_action = BranchPythonOperator(
        task_id='decide_action_based_on_result',
        python_callable=decide_action_based_on_result,
        provide_context=True,
    )

    # 步驟 6: 可能的動作
    task_download = PythonOperator(
        task_id='download_sanitized_file',
        python_callable=download_sanitized,
        provide_context=True,
    )

    task_report_clean = DummyOperator(task_id='report_clean')
    task_report_threat = DummyOperator(task_id='report_threat_detected')

    # 最終報告
    task_final_report = PythonOperator(
        task_id='final_report',
        python_callable=report_result,
        provide_context=True,
        trigger_rule='none_failed',
    )

    end = DummyOperator(task_id='end', trigger_rule='none_failed')

    # 定義流程
    start >> task_hash_lookup >> task_branch

    # 分支 1: 找到哈希
    task_branch >> task_report_existing >> task_final_report

    # 分支 2: 未找到哈希，需要掃描
    task_branch >> task_upload >> task_poll >> task_decide_action

    # 根據掃描結果的分支
    task_decide_action >> [task_download, task_report_clean, task_report_threat]

    # 匯總到最終報告
    [task_download, task_report_clean, task_report_threat] >> task_final_report

    task_final_report >> end
