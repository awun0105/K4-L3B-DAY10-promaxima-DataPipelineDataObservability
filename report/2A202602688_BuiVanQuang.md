# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Bùi Văn Quang              |
| MSSV               | 2A202602688                |
| Khóa/Lớp         | K4-L3B-DAY10               |
| Tên nhóm         | promaxima                  |
| Vai trò chính    | Observability & Evaluation (`quality.py` GX 1.x, `testset.py`, `metrics.py`, `reporting.py`) |
| Repository         | https://github.com/awun0105/K4-L3B-DAY10-promaxima-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26                 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Data Quality Gate & Freshness SLA | `src/observability/quality.py` | Clean Dataframe, Settings | Great Expectations suite result, Freshness SLA report | Hoàn thành |
| Benchmark Testset Generator | `src/evaluation/testset.py`, `src/evaluation/metrics.py` | Clean Dataframe | `data/eval/test_set.json` (10 câu test) | Hoàn thành |
| Báo cáo Markdown & Metrics Reporting | `src/observability/reporting.py` | Evaluation metrics, GX results | `data/reports/phase1_report.md`, `data/reports/corruption_report.md` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Thiết kế tín hiệu Quality Gate Alarm | Lâm Quang Anh Quân (Pipeline)        | Cung cấp cờ `quality["success"] == False` để kích hoạt Bonus B2 Auto Self-Healing |
| Kiểm thử tính toàn vẹn của Corpus   | Nguyễn Văn Diện (Data Foundation)    | Xác minh tập clean dataframe đáp ứng đủ 4 Expectations của GX 1.x |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Cài đặt Great Expectations 1.x suite | `src/observability/quality.py` | GX 1.x validation status | 4 Expectations kiểm định thành công |
| Thiết lập Freshness SLA (`age_days > 180`) | `src/observability/quality.py` | Freshness report | Tỷ lệ bài báo quá hạn < 25% |
| Sinh 10 câu hỏi Benchmark Testset | `src/evaluation/testset.py` | `data/eval/test_set.json` | 4 nhóm câu hỏi: summary, authors, date, categories |
| Xuất báo cáo đối chiếu định lượng 3 trạng thái | `src/observability/reporting.py` | `data/reports/corruption_report.md` | Bảng so sánh 3 cột Baseline vs Corrupted vs Repaired |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

File `data/quality/corrupted.json` bắt chính xác 2 vi phạm dữ liệu nghiêm trọng: `paper_id_unique` (phát hiện 4 bản ghi trùng lặp) và `summary_min_length` (phát hiện 2 bản ghi rỗng `""`), làm cơ sở dữ liệu tin cậy để kích hoạt chu trình tự phục hồi Bonus B2. Đồng thời tệp `data/reports/corruption_report.md` kết xuất bảng đối chiếu định lượng 3 trạng thái rõ ràng.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Trong hệ thống AI/RAG, sự suy giảm chất lượng dữ liệu thường diễn ra âm thầm (Silent Failure). Cần một chốt chặn kiểm định chất lượng tự động (Data Quality Gate) và giám sát độ trôi dạt tri thức (Freshness Monitoring) để kịp thời phát hiện vi phạm trước khi dữ liệu rác gây hại cho Agent.

### Cách triển khai

1. **Great Expectations 1.x Quality Gate:** Xây dựng Expectation Suite trên nền GX 1.x gồm 4 quy tắc cốt lõi:
   - `ExpectTableRowCountToBeBetween(min_value=10)`
   - `ExpectColumnValuesToNotBeNull(column="paper_id")`
   - `ExpectColumnValuesToBeUnique(column="paper_id")`
   - `ExpectColumnValueLengthsToBeBetween(column="summary", min_value=10)`
2. **Freshness SLA Monitoring:** Hàm `run_freshness_check()` kiểm tra khoảng cách ngày giữa thời điểm nạp (`ingested_at`) và ngày xuất bản (`published`). Nếu tỷ lệ tài liệu có `age_days > 180` vượt quá ngưỡng 25% (`max_stale_ratio = 0.25`), hệ thống kích hoạt cảnh báo vi phạm SLA.
3. **Standardized Test Set:** Hàm `build_test_set()` tự động trích xuất các bài báo trong clean corpus để sinh 10 câu hỏi trắc nghiệm thuộc 4 khía cạnh: `summary`, `authors`, `date`, `categories`, kèm theo danh sách `ground_truth_doc_ids` chính xác.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | Clean dataframe & Corrupted dataframe      |
| Output                         | Validation reports, Test set, Metrics reports |
| Module phụ thuộc             | `core/config.py`, `ingestion/cleaning.py`   |
| Module sử dụng output        | `pipelines`, evaluation runs                |
| Điều kiện lỗi cần xử lý | GX validation failures, nulls, schema mismatch |

### Cách xác minh

```bash
uv run python -c "from core.config import load_settings; from observability.quality import run_data_quality_checks; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); res=run_data_quality_checks(df, s, 'test'); print(f'Quality check status = {res[\"success\"]}')"
uv run python -c "from core.config import load_settings; from evaluation.testset import build_test_set; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); ts=build_test_set(df, s.paths.eval_testset); print(f'Sinh được {len(ts)} câu hỏi test')"
```

- **Kết quả mong đợi:** Quality check `success=True` trên clean data, sinh đúng 10 câu hỏi test.
- **Kết quả thực tế:** Quality check đạt `success=True` trên tập baseline và repaired; sinh đủ 10 câu hỏi test đa dạng 4 nhóm.
- **Artifact/log:** `data/eval/test_set.json`, `data/quality/baseline.json`, `data/reports/phase1_report.md`

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn phương pháp triển khai Great Expectations giữa việc dùng CLI cấu hình DataSource cồng kềnh và việc dùng GX Python API trực tiếp trên Pandas DataFrame.
- **Các phương án đã cân nhắc:**
  - *Phương án A:* Khởi tạo thư mục `gx/` bằng CLI, cấu hình context và datasource phức tạp.
  - *Phương án B:* Sử dụng GX 1.x In-Memory Batch Definition và Ephemeral Data Context trực tiếp trên Pandas DataFrame.
- **Phương án đã chọn:** Phương án B.
- **Lý do:** Giảm thiểu sự cồng kềnh của cấu hình file tĩnh, đảm bảo code hoàn toàn độc lập, dễ dàng chạy trong pipeline tự động và tương thích tuyệt đối với môi trường CI/CD hoặc container.
- **Bằng chứng quyết định phù hợp:** Hàm `run_data_quality_checks()` chạy nhẹ nhàng, hoàn tất kiểm tra và xuất báo cáo JSON trong chưa đầy 1 giây.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Lỗi API deprecation từ Great Expectations khi nâng cấp từ phiên bản cũ lên GX 1.x: `AttributeError: 'DataAsset' object has no attribute 'build_batch_request_with_data'`.
- **Lệnh hoặc bước tái hiện:** Chạy hàm kiểm định quality checks trên phiên bản Great Expectations 1.x.
- **Nguyên nhân gốc:** Great Expectations 1.x đã tái cấu trúc toàn diện API Fluent sang mô hình `context.data_sources.add_pandas().add_dataframe_asset().add_batch_definition_whole_dataframe()`.
- **Cách xử lý:** Cập nhật lại toàn bộ luồng tạo Ephemeral Data Context và Batch Request theo chuẩn GX 1.x API chính thức, đồng thời duy trì fallback an toàn kiểm tra trực tiếp qua Pandas để pipeline không bao giờ bị gián đoạn.
- **Cách xác minh sau khi sửa:** Chạy kiểm tra Quality Gate trên clean dataframe trả về đúng `{"success": True, "row_count": 24}`.
- **Điều học được:** Khi làm việc với các thư viện observability đang trong quá trình chuyển giao phiên bản lớn (như GX 1.x), cần đọc kỹ tài liệu di trú (Migration Guide) và xây dựng cơ chế graceful fallback.

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   Dữ liệu raw được nạp từ Crossref API hoặc snapshot → làm sạch và chuẩn hóa schema 14 trường → ghép trường `text_for_embedding` 5 phần → đưa qua SentenceTransformer `all-MiniLM-L6-v2` mã hóa vector → lưu vào ChromaDB collection.

2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   Bộ 10 câu hỏi test được thiết kế chứa tiêu đề bài báo trong ngoặc nháy `'...'` và gán nhãn `ground_truth_doc_ids`. Khi Agent truy vấn, hệ thống đo:
   - `retrieval_hit_rate`: Top-3 documents trả về có chứa ít nhất một `ground_truth_doc_ids` hay không.
   - `mean_token_f1`: Độ trùng khớp từ vựng giữa câu trả lời sinh ra và `ground_truth`.
   - `judge_accuracy` & `mean_judge_score`: Đánh giá ngữ nghĩa Pydantic từ LLM Judge (Gemini).

3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
   - Quality checks: Giám sát cấu trúc dữ liệu tĩnh (schema contract, giá trị null, tính duy nhất, độ dài).
   - Freshness monitoring: Giám sát thuộc tính động theo thời gian thực (độ tuổi tài liệu `age_days`, độ trôi dạt dữ liệu tri thức).

4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   Để duy trì tính nhất quán và loại bỏ biến gây nhiễu. Sự khác biệt về điểm số giữa 3 trạng thái chỉ có ý nghĩa khoa học khi được đo lường trên cùng một thang đo và cùng một tập câu hỏi.

5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   Dựa trên `data/reports/corruption_report.md`: Quality Gate chuyển lại `PASS`, Freshness SLA chuyển lại `FRESH`, `retrieval_hit_rate = 1.0000`, `mean_token_f1` hồi phục tuyệt đối từ 0.5611 lên 0.7076, và `judge_accuracy` đạt 0.8000.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |   1.0000 |    1.0000 |   1.0000 | Vector retrieval giữ vững độ phủ 100% nhờ top_k=3 |
| `mean_token_f1`      |   0.7076 |    0.5611 |   0.7076 | **Silent Failure:** F1 sụt giảm -0.1465 khi summary bị lỗi và phục hồi trọn vẹn sau repair |
| `judge_accuracy`     |   0.5000 |    0.6000 |   0.8000 | LLM judge đánh giá theo schema ngữ nghĩa nghiêm ngặt; bản repaired đạt độ chính xác cao nhất (80%) |
| `mean_judge_score`   |   3.4000 |    3.2000 |   3.6000 | Phản ánh đúng mức độ tin cậy của câu trả lời qua các pha |
| Quality checks         |     PASS |      FAIL |     PASS | GX 1.x bắt chính xác vi phạm ID trùng lặp (4 unexpected) và blank summary (2 bản ghi) |
| Freshness status       |    FRESH |     STALE |    FRESH | Cảnh báo vi phạm ngưỡng 25% bài báo quá hạn 180 ngày (tỷ lệ cũ vọt lên 31.82%) |

### Kết luận từ số liệu

1. **[Data corruption (blank summary + stale date)] → [Quality Gate báo FAIL và Freshness SLA báo STALE] → [Agent bị Silent Failure khi Token F1 giảm từ 0.7076 xuống 0.5611].**
2. **[Idempotent Repair kích hoạt qua Auto Self-Healing (Bonus B2)] → [Quality Gate và Freshness SLA xanh trở lại (PASS/FRESH)] → [Agent phục hồi hoàn toàn Token F1 về 0.7076 và Judge Score đạt 3.60].**

**Corruption nào ảnh hưởng rõ nhất và vì sao?**
Lỗi làm rỗng summary (`blank_summary`) ảnh hưởng nghiêm trọng nhất đến Agent vì làm mất toàn bộ nội dung tóm tắt kiến thức của bài báo, trực tiếp làm tụt giảm điểm số Token F1 trong khi vector search vẫn trả về văn bản.

**Kết quả nào khác với kỳ vọng ban đầu?**
`retrieval_hit_rate` không bị suy giảm dù bị tiêm lỗi cắt ngắn tiêu đề. Điều này chứng minh trường `text_for_embedding` gồm 5 phần (có authors, categories) đã bù đắp thông tin rất tốt cho vector similarity.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Data Observability:** Great Expectations 1.x đóng vai trò chốt chặn sống còn giúp ngăn chặn dữ liệu lỗi lọt vào vector database.
2. **Freshness SLA:** Việc theo dõi độ tuổi tri thức là bắt buộc đối với hệ thống RAG để tránh hiện tượng mô hình trả lời dựa trên tri thức đã lỗi thời.
3. **Controlled Benchmarking:** Giữ cố định test set và đánh giá định lượng đa chiều (Hit Rate, Token F1, LLM Judge) là phương pháp duy nhất để đo lường chính xác hiệu quả phục hồi.

### Nếu có thêm thời gian

Xây dựng hệ thống cảnh báo tự động gửi webhook tới Slack/Discord khi Freshness SLA hoặc Quality Gate bị vi phạm.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Bùi Văn Quang  
**Ngày xác nhận:** 2026-09-26  
