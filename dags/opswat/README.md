# OPSWAT MetaDefender Core DAGs

此目錄包含與 OPSWAT MetaDefender Core 整合的 Airflow DAG，提供高級惡意軟件檢測和文件消毒功能。

## 環境配置

在使用這些 DAG 之前，請設置以下環境變量：

```bash
export OPSWAT_API_URL="https://your-metadefender-core-url"
export OPSWAT_API_KEY="your-api-key"
```

或在 Airflow 的配置中設置這些變量。

## DAG 說明

### 1. dag_opswat_file_scan.py
**功能**: 上傳文件到 MetaDefender Core 進行多引擎掃描

**API**: `POST /file`

**使用場景**:
- 使用 30+ 防病毒引擎同時掃描文件
- 檢測已知惡意軟件
- 可選擇啟用動態分析和沙箱檢測

**參數**:
- `file_path`: 要掃描的文件路徑
- `archive_password`: 壓縮檔密碼（可選）
- `sample_sharing`: 樣本共享設置 (0/1)
- `dynamic_analysis`: 是否啟用動態分析 (0/1)

**輸出**:
- `data_id`: 用於後續查詢結果的唯一標識符

---

### 2. dag_opswat_hash_lookup.py
**功能**: 通過哈希值查詢文件是否已存在掃描記錄

**API**: `GET /hash/{hash}`

**使用場景**:
- 避免重複掃描已知文件
- 快速查詢文件的安全狀態
- 優化掃描流程，節省資源

**參數**:
- `file_path`: 文件路徑（用於計算哈希）
- `file_hash`: 文件哈希值（直接提供，可選）
- `hash_algorithm`: 哈希算法 (md5/sha1/sha256)

**輸出**:
- `hash_found`: 是否找到記錄 (True/False)
- `hash_lookup_result`: 查詢結果（如果找到）

---

### 3. dag_opswat_file_sanitize.py
**功能**: 使用 Deep CDR 技術清除文件中的潛在威脅

**API**: `POST /file` (workflow=sanitize)

**使用場景**:
- 清理可疑文件，生成安全版本
- 移除文件中的宏、腳本、嵌入對象等潛在威脅
- 支持 200+ 種文件格式

**參數**:
- `file_path`: 要消毒的文件路徑
- `archive_password`: 壓縮檔密碼（可選）
- `cdr_options`: CDR 配置選項（可選）
  - `removeAttachments`: 移除附件
  - `removeMacros`: 移除宏
  - `removeExternalLinks`: 移除外部連結

**輸出**:
- `data_id`: 用於下載清理後文件的標識符

---

### 4. dag_opswat_retrieve_results.py
**功能**: 獲取文件處理結果（掃描或消毒）

**API**: `GET /file/{data_id}`

**使用場景**:
- 查詢文件掃描/消毒的處理狀態
- 輪詢直到處理完成
- 獲取詳細的掃描結果和威脅信息

**參數**:
- `data_id`: 文件處理的唯一標識符
- `max_retries`: 最大重試次數（默認 30）
- `retry_interval`: 重試間隔秒數（默認 10）

**輸出**:
- `final_result`: 完整的處理結果
- `scan_result_i`: 掃描結果代碼
  - 0 = 無威脅
  - 1 = 已感染
  - 2 = 可疑
- `is_infected`: 是否檢測到威脅
- `total_detected_avs`: 檢測到威脅的引擎數量

---

### 5. dag_opswat_download_sanitized.py
**功能**: 下載經過 Deep CDR 處理後的清理文件

**API**: `GET /file/converted/{data_id}`

**使用場景**:
- 下載消毒後的安全文件
- 將清理後的文件保存到指定位置
- 獲取文件元數據

**參數**:
- `data_id`: 文件處理的唯一標識符
- `output_dir`: 輸出目錄（默認 /tmp/sanitized）
- `output_filename`: 輸出文件名

**輸出**:
- `sanitized_file_path`: 清理後文件的完整路徑
- `sanitized_file_size`: 文件大小
- `sanitized_filename`: 文件名

---

## 工作流示例

### 示例 1: 完整的文件掃描流程

```python
from airflow import DAG
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from datetime import datetime

with DAG(
    'dag_opswat_complete_scan_workflow',
    start_date=datetime(2025, 12, 29),
    schedule_interval=None,
    catchup=False,
) as dag:

    # 1. 先進行哈希查詢
    hash_lookup = TriggerDagRunOperator(
        task_id='hash_lookup',
        trigger_dag_id='dag_opswat_hash_lookup',
        conf={'file_path': '/tmp/test_file.txt'},
    )

    # 2. 如果未找到，進行掃描
    file_scan = TriggerDagRunOperator(
        task_id='file_scan',
        trigger_dag_id='dag_opswat_file_scan',
        conf={'file_path': '/tmp/test_file.txt'},
    )

    # 3. 獲取結果
    retrieve_results = TriggerDagRunOperator(
        task_id='retrieve_results',
        trigger_dag_id='dag_opswat_retrieve_results',
    )

    hash_lookup >> file_scan >> retrieve_results
```

### 示例 2: 文件消毒流程

```python
from airflow import DAG
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from datetime import datetime

with DAG(
    'dag_opswat_sanitize_workflow',
    start_date=datetime(2025, 12, 29),
    schedule_interval=None,
    catchup=False,
) as dag:

    # 1. 提交文件消毒
    sanitize = TriggerDagRunOperator(
        task_id='sanitize_file',
        trigger_dag_id='dag_opswat_file_sanitize',
        conf={'file_path': '/tmp/suspicious_file.docx'},
    )

    # 2. 等待處理完成並獲取結果
    retrieve_results = TriggerDagRunOperator(
        task_id='retrieve_results',
        trigger_dag_id='dag_opswat_retrieve_results',
    )

    # 3. 下載清理後的文件
    download = TriggerDagRunOperator(
        task_id='download_sanitized',
        trigger_dag_id='dag_opswat_download_sanitized',
    )

    sanitize >> retrieve_results >> download
```

## MetaDefender Core 主要功能

### 1. Multiscanning (多引擎掃描)
- 使用 30+ 頂級防病毒引擎
- 檢測超過 99% 的已知惡意軟件
- 提供詳細的威脅信息

### 2. Deep CDR (內容消毒與重建)
- 支持 200+ 種文件格式
- 移除 100% 的潛在威脅
- 保留文件的可用性和格式

### 3. Adaptive Sandbox (自適應沙箱)
- 基於仿真的行為分析
- 檢測未知威脅和零日攻擊
- 提供詳細的 IOC (威脅指標)

## API 文檔參考

- [MetaDefender Core 官方文檔](https://docs.opswat.com/mdcore/)
- [MetaDefender Core API 參考](https://docs.opswat.com/mdcore/metadefender-core/ref)
- [REST API (v2) 文檔](https://onlinehelp.opswat.com/corev3/REST_API_(v2).html)

## 注意事項

1. **API Key 安全**: 請妥善保管您的 API Key，不要將其提交到版本控制系統
2. **超時設置**: 大文件掃描可能需要較長時間，請適當調整超時和重試參數
3. **文件大小限制**: MetaDefender Core 對文件大小可能有限制，請查閱官方文檔
4. **並發限制**: 注意 API 的並發請求限制，避免超出配額

## 許可證

此代碼遵循項目的主許可證。MetaDefender Core 是 OPSWAT 公司的商業產品。
