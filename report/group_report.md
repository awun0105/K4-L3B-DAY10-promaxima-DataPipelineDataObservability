# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Khóa/Lớp         | K4-L3B-DAY10               |
| Tên nhóm         | promaxima                  |
| Repository         | https://github.com/awun0105/K4-L3B-DAY10-promaxima-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26                 |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Lâm Quang Anh Quân | 2A202602467 | Trưởng nhóm / Pipeline Integrator & Recovery | `src/core/`, `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py`, `script/run_phase1.py`, `script/run_corruption_flow.py` |
| 2 | Nguyễn Văn Diện | 2A202602615 | Data Foundation & RAG Vector Index | `src/ingestion/crossref.py`, `src/ingestion/cleaning.py`, `src/retrieval/embeddings.py`, `src/retrieval/index.py`, `src/ingestion/corruption.py` |
| 3 | Bùi Văn Quang | 2A202602688 | Observability & Evaluation | `src/observability/quality.py`, `src/observability/reporting.py`, `src/evaluation/testset.py`, `src/evaluation/metrics.py`, `src/evaluation/ragas_eval.py` |

## 2. Tóm tắt kết quả

Nhóm **promaxima** đã hoàn thành trọn vẹn toàn bộ 10 bước của Pha 1 (Baseline Pipeline) và quy trình điều phối khép kín của Pha 2 (Corruption, Quality Gate & Idempotent Repair Flow) cùng tính năng nâng cao **Bonus B2 (Auto Self-Healing)**. 

Trong Pha 1, hệ thống thu thập 24 bản ghi nghiên cứu từ Crossref API (hỗ trợ fallback snapshot cục bộ bất biến), thực hiện làm sạch dữ liệu theo data contract 14 trường, tạo `text_for_embedding` 5 phần, đánh chỉ mục ChromaDB collection `papers-baseline` và đánh giá tự động trên bộ 10 câu hỏi test set. Kết quả baseline đạt `retrieval_hit_rate = 1.0000`, `mean_token_f1 = 0.7076`, Quality Gate đạt **PASS** và Freshness SLA đạt **FRESH** (tỷ lệ cũ chỉ 4.17%).

Trong Pha 2, nhóm tiêm 6 kịch bản lỗi dữ liệu tổng hợp. Lỗi làm rỗng summary và nhân bản dòng đã khiến Great Expectations 1.x kích hoạt cảnh báo vi phạm (**FAIL**), trong khi lỗi lùi ngày xuất bản đẩy tỷ lệ stale lên 31.82%, vi phạm Freshness SLA (**STALE**). Mặc dù vector search vẫn giữ được hit rate do top-3 coverage, chất lượng câu trả lời bị hiện tượng **Silent Failure** nghiêm trọng với `mean_token_f1` giảm sâu -0.1465 (xuống 0.5611). Nhờ cơ chế **Auto Self-Healing (Bonus B2)**, hệ thống tự động phát hiện vi phạm và thực hiện **Idempotent Repair** từ raw snapshot bất biến, đưa Quality Gate trở lại **PASS**, Freshness trở lại **FRESH**, và khôi phục hoàn toàn `mean_token_f1` về 0.7076 cùng `judge_accuracy` đạt 0.8000.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref API / Fallback Snapshot
    -> Raw response/records (data/raw/crossref_records.json)
    -> Ingestion & Data Cleaning (5-part text_for_embedding, age_days, schema contract)
    -> SentenceTransformer (all-MiniLM-L6-v2) + ChromaDB index (papers-baseline)
    -> Evaluation Baseline (10-question standardized test set -> hit rate, token F1, Gemini LLM Judge)
    -> Observability (Great Expectations 1.x Quality Gate & Freshness SLA 180 days)
    -> Synthetic Corruption (6 scenarios -> papers_clean_corrupted -> papers-corrupted)
    -> Re-evaluate Corrupted (Silent Failure detection)
    -> Auto Self-Healing / Idempotent Repair (triggered by failed Quality Gate, rebuilt from raw records)
    -> Re-evaluate Repaired + Quality Gate verification
    -> Markdown Comparison Report (3-state benchmark) & Live Console Demo
```

### Trách nhiệm của từng khối

| Khối             | Input          | Xử lý chính             | Output/artifact          | Owner          |
| ----------------- | -------------- | -------------------------- | ------------------------ | -------------- |
| Ingestion         | Crossref REST API / Snapshot | Fetch, retry backoff, fallback parsing, schema mapping | `data/raw/crossref_records.json` | Nguyễn Văn Diện |
| Cleaning          | Raw records list | Làm sạch HTML/XML, chuẩn hóa ngày, tính `age_days`, khử trùng lặp, ghép 5 phần `text_for_embedding` | `data/clean/papers_clean.csv`, `papers_clean.json` | Nguyễn Văn Diện |
| Embedding/index   | Cleaned DataFrame | Mô hình hóa vector bằng `all-MiniLM-L6-v2`, lập chỉ mục ChromaDB PersistentClient | `data/chroma/`, `data/embeddings/papers_embeddings.json` | Nguyễn Văn Diện |
| Evaluation        | Vector index, Test set | Đánh giá Retrieval Top-3, Token F1, Gemini LLM-as-a-Judge | `data/eval/test_set.json`, `data/results/*_metrics.json` | Bùi Văn Quang |
| Observability     | Cleaned/Corrupted DataFrame | Great Expectations 1.x Expectation Suite, Freshness SLA check (180 ngày) | `data/quality/*.json` | Bùi Văn Quang |
| Corruption/repair | Clean DataFrame, Raw snapshot | Tiêm 6 kịch bản lỗi tổng hợp, Idempotent repair từ raw records | `data/results/corruption_log.json`, `data/clean/papers_clean_repaired.json` | Nguyễn Văn Diện & Lâm Quang Anh Quân |
| Orchestration     | Toàn bộ config (`Settings`) | Khép kín 10 bước Pha 1 & chu trình 7 bước Pha 2 kèm Bonus B2 Self-Healing | `data/reports/phase1_report.md`, `data/reports/corruption_report.md` | Lâm Quang Anh Quân |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình             | Giá trị sử dụng |
| ---------------------------- | ------------------- |
| `LLM_PROVIDER`             | gemini              |
| `LLM_MODEL`                | gemini-flash-latest |
| Embedding model              | sentence-transformers/all-MiniLM-L6-v2 |
| Số lượng Crossref records | 24                  |
| Retrieval `top_k`           | 3                   |
| Freshness threshold          | 180 days (tỷ lệ vi phạm tối đa 0.25) |
| Random seed                  | 42                  |

### Lệnh cài đặt

```bash
uv sync
```

### Lệnh chạy

Baseline Pipeline (Pha 1):

```bash
uv run python script/run_phase1.py
```

Corruption, Repair & Auto Self-Healing Flow (Pha 2):

```bash
uv run python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh             | Trạng thái                                    | Thời điểm chạy gần nhất | Bằng chứng                         |
| ----------------- | ----------------------------------------------- | ----------------------------- | ------------------------------------ |
| Baseline pipeline | Thành công (Exit code 0)                        | 2026-09-26 11:29:43+07:00     | `data/reports/phase1_report.md`, `data/results/baseline_metrics.json` |
| Corruption flow   | Thành công (Exit code 0)                        | 2026-09-26 11:39:15+07:00     | `data/reports/corruption_report.md`, `data/results/repaired_metrics.json` |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính                | Giá trị                             |
| --------------------------- | ------------------------------------- |
| Source                      | Crossref REST API (`https://api.crossref.org/works`) kết hợp Fallback snapshot |
| Query/filter                | `query=data+pipeline+observability+rag`, `filter=type:journal-article`, `rows=24` |
| Thời điểm lấy dữ liệu | 2026-09-26T04:27:00Z                 |
| Số record nhận được    | 24                                  |
| Cơ chế retry/backoff      | Tenacity retry 3 lần với exponential backoff (`min=2s`, `max=10s`), tự động fallback sang `crossref_response.json` khi có sự cố mạng |

### Raw và clean schema

| Trường        | Kiểu dữ liệu | Bắt buộc?  | Ý nghĩa   | Xử lý khi thiếu/sai |
| --------------- | --------------- | ------------ | ----------- | ---------------------- |
| `paper_id`      | string          | Có           | Khóa định danh duy nhất (DOI hoặc prefix `crossref:`) | Chuẩn hóa prefix hoặc gán mã duy nhất |
| `title`         | string          | Có           | Tiêu đề bài báo nghiên cứu | Strip whitespace, loại bỏ HTML tags; nếu thiếu báo lỗi |
| `authors`       | string          | Không        | Danh sách tên tác giả ghép chuỗi | Nối danh sách bằng dấu phẩy; nếu rỗng để `"Unknown"` |
| `abstract`      | string          | Không        | Tóm tắt học thuật đầy đủ từ Crossref | Xóa bỏ thẻ XML/JATS; nếu thiếu thay bằng chuỗi rỗng |
| `summary`       | string          | Có           | Tóm tắt rút gọn tối đa 500 ký tự | Cắt từ abstract hoặc fallback từ title |
| `published`     | string (ISO)    | Có           | Ngày xuất bản chuẩn `YYYY-MM-DD` | Parse các phần `date-parts`; nếu thiếu fallback ngày hiện tại |
| `journal`       | string          | Không        | Tên tạp chí hoặc kỷ yếu xuất bản | Lấy `container-title`; nếu rỗng để `"Unknown Journal"` |
| `doi`           | string          | Có           | Mã DOI định danh quốc tế | Giữ nguyên format DOI chuẩn |
| `categories`    | string          | Không        | Phân loại chuyên ngành (subject) | Nối các chuyên ngành; nếu rỗng để `"General"` |
| `source`        | string          | Có           | Nguồn thu thập dữ liệu | Mặc định gán `"crossref"` |
| `ingested_at`   | string (ISO)    | Có           | Thời điểm dữ liệu được nạp vào hệ thống | Timestamp hiện tại định dạng ISO 8601 UTC |
| `age_days`      | integer         | Có           | Số ngày tính từ lúc xuất bản đến lúc nạp | `(ingested_at - published).days`, ép kiểu int >= 0 |
| `is_stale`      | boolean         | Có           | Cờ đánh dấu tài liệu quá hạn | `True` nếu `age_days > 180`, ngược lại `False` |
| `text_for_embedding` | string     | Có           | Văn bản tổng hợp 5 phần chuẩn phục vụ sinh vector | Ghép có cấu trúc từ Title, Authors, Published, Categories, Summary |

### Quy tắc cleaning

| Quy tắc                                 | Quality dimension liên quan | Số record bị tác động | Cách xác minh      |
| ---------------------------------------- | ---------------------------- | -------------------------: | -------------------- |
| Loại bỏ thẻ HTML/XML (`<jats:p>`, v.v.)  | Validity                     | 24                         | Kiểm tra regex trong `abstract` không còn ký tự `<...>` |
| Khử trùng lặp theo `paper_id` & `doi`    | Uniqueness                   | 0 (baseline) / 2 (corrupted) | Great Expectations `ExpectColumnValuesToBeUnique` |
| Bắt buộc độ dài tối thiểu của `summary`  | Completeness                 | 2 (khi bị tiêm lỗi)        | Great Expectations `ExpectColumnValueLengthsToBeBetween` |
| Chuẩn hóa ngày và tính toán `age_days`   | Consistency & Timeliness     | 24                         | Kiểm tra `age_days >= 0` và đối chiếu Freshness SLA |

**Giải thích cách tạo `text_for_embedding`, document ID và `age_days`:**
- `text_for_embedding`: Ghép 5 trường cốt lõi theo mẫu:
  ```text
  Title: {title}
  Authors: {authors}
  Published: {published}
  Categories: {categories}
  Summary: {summary}
  ```
  Cách tổ chức này cung cấp đầy đủ ngữ cảnh cho mô hình dense vector, giúp mô hình nắm bắt cả thông tin thực thể (tác giả, ngày xuất bản) lẫn nội dung học thuật.
- `paper_id` (Document ID): Sử dụng trực tiếp mã DOI chuẩn (ví dụ: `10.1145/3637528.3671812`).
- `age_days`: Được tính bằng hiệu số ngày giữa ngày thu thập (`ingested_at`) và ngày công bố bài báo (`published`). Nếu bài báo có `age_days > 180`, bài báo được gắn nhãn `is_stale = True`.

## 6. Evaluation setup

| Thành phần                             | Cấu hình thực tế          |
| ---------------------------------------- | ----------------------------- |
| Số câu hỏi                            | 10 câu hỏi chuẩn hóa          |
| Các `question_type`                    | `summary`, `authors`, `date`, `categories` |
| Ground-truth document ID                 | Trích xuất trực tiếp từ `paper_id` của tập dữ liệu sạch khi sinh test set |
| Embedding model                          | `sentence-transformers/all-MiniLM-L6-v2` (384 chiều) |
| Vector store/collection                  | ChromaDB (`papers-baseline`, `papers-corrupted`, `papers-repaired`) |
| Retrieval `top_k`                       | 3                             |
| LLM provider/model                       | `gemini` / `gemini-flash-latest` (đáp ứng LLM-as-a-Judge với Pydantic schema `JudgeVerdict`) |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json`     |

**Giải thích vì sao test set được giữ nguyên khi đánh giá baseline, corrupted và repaired:**
Việc giữ nguyên tập test set và ground truth cố định xuyên suốt cả 3 trạng thái là nguyên tắc then chốt của phương pháp thực nghiệm khoa học có đối chứng (Controlled Experiment). Khi bộ câu hỏi và tiêu chí đánh giá được cố định hoàn toàn, bất kỳ sự thay đổi nào về chỉ số retrieval (`retrieval_hit_rate`) và chỉ số chất lượng câu trả lời (`mean_token_f1`, `mean_judge_score`) đều phản ánh chính xác tác động của việc tiêm lỗi dữ liệu và hiệu quả phục hồi của quy trình sửa chữa, loại trừ tuyệt đối yếu tố gây nhiễu do độ khó không đồng đều giữa các câu hỏi khác nhau.

## 7. Kết quả baseline

### Artifact checklist

| Artifact                 | Đường dẫn thực tế                | Trạng thái | Ghi chú   |
| ------------------------ | -------------------------------------- | ------------ | ---------- |
| Raw response/records     | `data/raw/crossref_records.json`       | Có           | 24 bản ghi thô từ Crossref API / Fallback snapshot |
| Cleaned dataset          | `data/clean/papers_clean.csv`, `.json` | Có           | 24 bản ghi sạch, đầy đủ 14 trường theo hợp đồng dữ liệu |
| Embedding manifest/index | `data/embeddings/papers_embeddings.json`, `data/chroma/` | Có | Vector store ChromaDB collection `papers-baseline` |
| Evaluation set           | `data/eval/test_set.json`              | Có           | 10 câu hỏi benchmark đa dạng các khía cạnh truy vấn |
| Baseline metrics         | `data/results/baseline_metrics.json`   | Có           | Kết quả benchmark Pha 1 hoàn chỉnh |
| Quality/freshness        | `data/quality/baseline.json`, `freshness_report.json` | Có | Great Expectations PASS, Freshness FRESH |
| Baseline report          | `data/reports/phase1_report.md`        | Có           | Báo cáo Markdown Pha 1 đầy đủ số liệu |

### Baseline metrics

| Metric                 |       Giá trị | Diễn giải                             |
| ---------------------- | --------------: | --------------------------------------- |
| `retrieval_hit_rate` |        1.0000 | 100% câu hỏi truy vấn tìm thấy đúng document chứa thông tin trong top-3 kết quả |
| `mean_token_f1`      |        0.7076 | Điểm số trùng khớp từ vựng trung bình giữa câu trả lời sinh ra và ground truth đạt mức cao |
| `judge_accuracy`     |        0.5000 | Tỷ lệ câu trả lời được Gemini Judge đánh giá chính xác theo tiêu chí ngữ nghĩa nghiêm ngặt |
| `mean_judge_score`   |        3.4000 | Điểm chất lượng trung bình (thang 1-5) từ LLM-as-a-Judge cho câu trả lời baseline |
| Ragas, nếu có        | N/A (Skipped)   | Bỏ qua để tối ưu thời gian chạy và tránh cạn kiệt quota API Gemini (kích hoạt bằng `RUN_RAGAS=1`) |

## 8. Data quality và freshness

### Quality checks

| Check        | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline      | Bằng chứng |
| ------------ | ----------------- | ------------------ | ----------------------- | ------------ |
| `table_row_count` | Completeness | Min = 10 bản ghi | PASS (24 bản ghi) | `data/quality/baseline.json` |
| `paper_id_not_null` | Completeness | Unexpected = 0 | PASS (0 nulls) | `data/quality/baseline.json` |
| `paper_id_unique` | Uniqueness | Unexpected = 0 | PASS (0 duplicates) | `data/quality/baseline.json` |
| `summary_min_length` | Validity / Completeness | Min length = 10 ký tự | PASS (0 bản ghi vi phạm) | `data/quality/baseline.json` |

### Freshness

| Thuộc tính               | Giá trị                           |
| -------------------------- | ----------------------------------- |
| Freshness được đo tại | Tập dữ liệu sạch `data/clean/papers_clean.json` |
| Timestamp mới nhất       | 2026-07-22                          |
| Ngưỡng freshness         | `stale_threshold_days = 180`, `max_stale_ratio = 0.25` |
| Trạng thái baseline      | FRESH                               |
| Lý do                     | Chỉ có 1 bản ghi cũ hơn 180 ngày (tỷ lệ 4.17%), thấp hơn rất nhiều so với ngưỡng cảnh báo 25% |

## 9. Corruption scenarios và repair

| Corruption         | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair   |
| ------------------ | ---------- | ---------------------: | ------------------------ | --------------------- | -------------- |
| 1. Drop latest records | Xóa 4 bản ghi mới nhất theo ngày xuất bản (20% corpus) | 4 | Freshness giảm, ngày mới nhất lùi về quá khứ | Ngày mới nhất lùi từ 2026-07-22 về 2026-06-12 | Tái nạp toàn bộ từ raw snapshot |
| 2. Blank summary | Xóa rỗng trường `summary` | 2 | `summary_min_length` thất bại | Quality Gate FAIL (2 bản ghi rỗng `""`) | Tái tạo summary từ raw abstract/title |
| 3. Inject noise | Chèn chuỗi ký tự rác vào `summary` | 2 | Suy giảm chất lượng ngữ nghĩa | Gây Silent Failure, suy giảm Token F1 của câu trả lời | Khôi phục nguyên bản từ raw records |
| 4. Truncate title | Cắt ngắn tiêu đề bài báo xuống < 8 ký tự | 2 | Sai lệch ngữ nghĩa tìm kiếm | Tiêu đề bị biến dạng (`Semant`, `Chunki`) | Khôi phục title gốc từ raw records |
| 5. Stale date | Lùi ngày xuất bản về quá khứ 5 năm (2021) | 6 | Vi phạm Freshness SLA | Tỷ lệ stale vọt lên 31.82% (> 25%), Freshness = STALE | Khôi phục `published` gốc |
| 6. Duplicate rows | Nhân bản 2 bản ghi để tạo ID trùng lặp | 2 | `paper_id_unique` thất bại | Quality Gate FAIL (4 unexpected duplicates) | Khử trùng lặp qua logic Data Cleaning |

**Corruption log:**
- Đường dẫn: `data/results/corruption_log.json`
- Trạng thái: Có đầy đủ
- Nhận xét: Ghi nhận chính xác timestamp, số lượng dòng trước và sau khi tiêm lỗi (24 -> 22), chi tiết từng kịch bản và danh sách ID của toàn bộ các bản ghi bị ảnh hưởng.

**Giải thích cách repair đảm bảo dữ liệu được phục hồi từ nguồn đáng tin cậy:**
Hệ thống kiên quyết từ chối việc sửa chữa chắp vá (ad-hoc patching) trên tệp dữ liệu đã bị biến dạng. Thay vào đó, quy trình triển khai nguyên lý **Idempotent Data Repair**: truy xuất lại toàn bộ từ tệp dữ liệu thô gốc bất biến (`data/raw/crossref_records.json`), chạy lại toàn bộ quy trình làm sạch chuẩn hóa `build_clean_dataframe()` để áp dụng mọi quy tắc khử trùng lặp và tính toán trường dẫn xuất, xuất ra `papers_clean_repaired.json` và tái tạo mới hoàn toàn collection ChromaDB `papers-repaired`. Điều này đảm bảo trạng thái phục hồi là tất định, nhất quán và độc lập với các lỗi tiêm vào trước đó.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal            | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét   |
| ------------------------ | -------: | --------: | -------: | -----------------------: | --------------: | ------------ |
| `retrieval_hit_rate`   |   1.0000 |    1.0000 |   1.0000 |                   0.0000 |          0.0000 | Không suy giảm do `top_k=3` vẫn bao quát được tài liệu liên quan |
| `mean_token_f1`        |   0.7076 |    0.5611 |   0.7076 |                  -0.1465 |         +0.1465 | **Silent Failure**: F1 giảm mạnh 14.65% do summary bị nhiễu và xóa rỗng, phục hồi 100% sau repair |
| `judge_accuracy`       |   0.5000 |    0.6000 |   0.8000 |                  +0.1000 |         +0.2000 | LLM Judge đánh giá theo tiêu chí ngữ nghĩa nghiêm ngặt; bản repaired đạt độ chính xác cao nhất (80%) |
| `mean_judge_score`     |   3.4000 |    3.2000 |   3.6000 |                  -0.2000 |         +0.4000 | Điểm số đánh giá chất lượng giảm khi có nhiễu và tăng vượt trội khi sửa lỗi |
| Quality checks pass/fail |     PASS |      FAIL |     PASS | Vi phạm 2 expectations   |    Khôi phục đủ | Great Expectations 1.x bắt chính xác vi phạm ID trùng lặp và độ dài summary |
| Freshness status         |    FRESH |     STALE |    FRESH | Tỷ lệ stale: 4.2% -> 31.8% | Trở lại 4.17% | Freshness SLA bắt chính xác việc lùi ngày xuất bản vi phạm ngưỡng 25% |

**Hai kết luận có quan hệ nhân quả được hỗ trợ bởi artifacts:**

1. **Chuỗi vi phạm và Silent Failure:** Việc tiêm lỗi rỗng tóm tắt (`blank_summary`) và nhiễu (`inject_noise`) trực tiếp kích hoạt cảnh báo vi phạm Great Expectations (`summary_min_length` thất bại) và Freshness SLA (`is_fresh = False`). Dù ứng dụng không bị crash và retrieval vẫn tìm thấy tài liệu, nội dung văn bản bị nhiễu khiến câu trả lời của Agent mất thông tin trọng yếu, thể hiện rõ qua sự sụt giảm định lượng của `mean_token_f1` từ 0.7076 xuống 0.5611 (-0.1465).
2. **Chuỗi phục hồi tự động (Bonus B2):** Khi Quality Gate phát tín hiệu cảnh báo vi phạm (`success=False`), bộ điều khiển tự phục hồi (Auto Self-Healing) lập tức kích hoạt luồng Idempotent Repair từ snapshot thô bất biến `crossref_records.json`. Quá trình tái tạo giúp Great Expectations chuyển xanh trở lại (`success=True`), Freshness đạt trạng thái `FRESH` (tỷ lệ cũ chỉ 4.17%), đồng thời khôi phục trọn vẹn điểm số `mean_token_f1` lên 0.7076 (+0.1465) và đưa `mean_judge_score` lên mức cao nhất 3.6000.

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** Khi chạy module đánh giá với mô hình mặc định `gemini-2.5-flash`, Google Gemini API trả về lỗi HTTP 404 NOT_FOUND (`models/gemini-2.5-flash is not found for API version v1beta`), đồng thời gặp lỗi HTTP 429 RESOURCE_EXHAUSTED do chạm ngưỡng giới hạn tốc độ 5 requests/phút của Gemini API Free Tier trong các lần chạy liên tục.
- **Nguyên nhân:** Tên định danh model `gemini-2.5-flash` chưa được hỗ trợ đầy đủ trên endpoint API cá nhân v1beta, đồng thời bài test gồm 10 câu hỏi chạy liên tiếp vượt quá hạn mức 5 RPM của gói miễn phí.
- **Cách xử lý:** Nhóm chuyển đổi cấu hình sang `gemini-flash-latest` (hỗ trợ trơn tru Pydantic Structured Output cho `JudgeVerdict`), đồng thời áp dụng thư viện `tenacity` với chiến lược exponential backoff thông minh (`wait_exponential(multiplier=2, min=10, max=60)`). Khi gặp lỗi 429, tiến trình tự động tạm dừng và chờ đợi qua chu kỳ quota trước khi retry mà không làm gián đoạn pipeline.
- **Cách xác minh:** Chạy trọn vẹn `script/run_phase1.py` và `script/run_corruption_flow.py`, toàn bộ 20 lượt đánh giá LLM-as-a-Judge đều thành công và trả về mã thoát 0.

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng   | Hướng cải thiện có thể kiểm chứng |
| --------------------- | -------------- | ----------------------------------------- |
| Quota giới hạn 5 RPM của Gemini Free Tier | Thời gian chạy pipeline đánh giá bị kéo dài do phải dừng chờ hồi quota | Tích hợp cơ chế batch evaluation hoặc triển khai mô hình LLM cục bộ (Ollama/vLLM) cho các bài đánh giá offline |
| Bộ test set cố định 10 câu hỏi | Chưa kiểm thử được hết các trường hợp truy vấn phức tạp hoặc câu hỏi đa bước (multi-hop) | Mở rộng quy mô test set lên 50-100 câu hỏi với độ phủ rộng hơn và các câu hỏi đối nghịch (adversarial queries) |
| Chỉ mục vector thuần dense retrieval | Có thể bỏ sót các từ khóa chuyên ngành hiếm hoặc mã số định danh đặc thù | Triển khai Hybrid Search kết hợp BM25 (sparse) và Dense Vector kèm mô hình Cross-Encoder Reranker |

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác.
- [x] Phân công khớp với module, artifact và kết quả thực tế.
- [x] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp.
- [x] Baseline, corrupted và repaired dùng cùng evaluation set.
- [x] Bảng metrics khớp với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp với `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact truy cập được.
- [x] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng.
- [x] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh.
