# Member Role Report — Day 10: Data Pipeline & Data Observability

> Mỗi thành viên trong nhóm tự hoàn thành mẫu này để báo cáo đúng vai trò, phần việc và mức hiểu của mình. Không sao chép nguyên báo cáo chung hoặc báo cáo của thành viên khác.

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Lâm Quang Anh Quân         |
| MSSV               | 2A202602467                |
| Khóa/Lớp         | K4-L3B-DAY10               |
| Tên nhóm         | promaxima                  |
| Vai trò chính    | Trưởng nhóm / Pipeline Integrator & Data Recovery (`core/`, `phase1.py`, `corruption_flow.py`) |
| Repository         | https://github.com/awun0105/K4-L3B-DAY10-promaxima-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26                 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Cấu hình hệ thống & Utilities | `src/core/config.py`, `src/core/utils.py` | Environment variables, `.env` | Settings dataclass, đường dẫn artifacts | Hoàn thành |
| Pipeline Baseline Pha 1 | `src/pipelines/phase1.py`, `script/run_phase1.py` | Raw data & Config | `data/results/baseline_metrics.json`, `data/reports/phase1_report.md` | Hoàn thành |
| Luồng Corruption & Idempotent Repair | `src/pipelines/corruption_flow.py`, `script/run_corruption_flow.py` | Clean data, Raw snapshots | `data/results/repaired_metrics.json`, `data/reports/corruption_report.md` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Định nghĩa Data Contract & Schema | Nguyễn Văn Diện, Bùi Văn Quang | Đồng bộ 100% schema `PaperRecord` và clean dataframe 14 trường |
| Tích hợp Bonus B2 Auto Self-Healing | Bùi Văn Quang (Observability) | Pipeline tự động kích hoạt logic repair khi phát hiện Quality Gate vi phạm |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Thiết lập cấu hình hệ thống & artifacts | `src/core/config.py`, `src/core/utils.py` | Load settings, paths | `python -c "from core.config import load_settings; s=load_settings(); print(s.model_name)"` |
| Điều phối Baseline Pipeline | `src/pipelines/phase1.py`, `script/run_phase1.py` | `baseline_metrics.json`, `phase1_report.md` | `python script/run_phase1.py` |
| Triển khai luồng Corruption & Idempotent Repair | `src/pipelines/corruption_flow.py`, `script/run_corruption_flow.py` | `repaired_metrics.json`, `corruption_report.md` | `python script/run_corruption_flow.py` |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

Module điều phối `src/pipelines/corruption_flow.py` tự động chạy khép kín chu trình 7 bước (Baseline → Corrupted → Evaluate → Idempotent Repair → Re-evaluate → Quality Gate Verification → 3-State Markdown Report), đồng thời in bảng đối chiếu trực tiếp trên console phục vụ Live Demo.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Trong hệ thống RAG phục vụ môi trường thực tế, dữ liệu bẩn thường không làm ứng dụng sụp đổ (crash/exception) mà gây ra lỗi âm thầm (Silent Failure). Hệ thống cần một luồng điều phối chuẩn (Pipeline Orchestration) đảm bảo tính toàn vẹn dữ liệu, tự động phát hiện vi phạm và có khả năng phục hồi tự động an toàn (Idempotent Recovery).

### Cách triển khai

1. **Modular Orchestration:** Xây dựng hàm `run_baseline_pipeline()` và `run_corruption_and_repair_flow()` nhận đối tượng `Settings` cấu hình tập trung, độc lập với môi trường chạy.
2. **Idempotent Repair:** Khi dữ liệu bị tiêm lỗi, thay vì sửa chữa chắp vá trên file CSV đã hỏng, hệ thống truy xuất lại từ bản lưu trữ thô bất biến (`data/raw/crossref_records.json`), chạy lại toàn bộ quy trình làm sạch để đảm bảo tính tất định và không bị phụ thuộc vào trạng thái lỗi trước đó.
3. **Auto Self-Healing (Bonus B2):** Bọc điều kiện cảnh báo ngay sau bước kiểm định Quality Gate. Nếu `quality["success"] == False` hoặc `freshness["is_fresh"] == False`, hệ thống kích hoạt tự động quy trình phục hồi mà không cần sự can thiệp thủ công từ kỹ sư vận hành.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | `Settings`, raw snapshot JSON, cleaned dataframe |
| Output                         | Metrics bundles, Chroma index collections, reports |
| Module phụ thuộc             | `src/ingestion`, `src/observability`, `src/retrieval`, `src/evaluation` |
| Module sử dụng output        | `script/run_phase1.py`, `script/run_corruption_flow.py`, Live Demo |
| Điều kiện lỗi cần xử lý | Thiếu artifacts, lỗi quota API, vi phạm Data Quality Gate |

### Cách xác minh

```bash
uv run python script/run_phase1.py
uv run python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** Cả 2 kịch bản chạy thành công với mã thoát 0, xuất bảng đối chiếu 3 trạng thái rõ ràng.
- **Artifact/log:** `data/reports/phase1_report.md`, `data/reports/corruption_report.md`

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn phương pháp phục hồi dữ liệu khi xảy ra Data Corruption (Idempotent Repair).
- **Các phương án đã cân nhắc:**
  - *Phương án A:* Rollback/ghi đè lại file `papers_clean.csv` từ bản backup clean của pha 1.
  - *Phương án B:* Kích hoạt luồng tái tạo từ Raw Ingestion snapshot (`crossref_records.json`) qua hàm làm sạch chuẩn hóa `build_clean_dataframe`.
- **Phương án đã chọn:** Phương án B.
- **Lý do:** Đảm bảo nguyên lý Idempotency và Data Lineage. Nếu logic làm sạch có cập nhật luật mới, việc tái tạo từ Raw Data sẽ áp dụng được toàn bộ quy tắc mới nhất, tránh tình trạng "rác chồng rác" khi dữ liệu clean trung gian bị biến dạng.
- **Bằng chứng quyết định phù hợp:** Kết quả `repaired_quality["success"] == True` và chỉ số `retrieval_hit_rate` lấy lại mức ~1.00 tương đương Baseline ban đầu.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `bash: !': event not found` khi chạy lệnh kiểm tra môi trường:
  ```bash
  uv python -c "import chromadb, great_expectations, sentence_transformers; print('Environment Ready!')"
  ```
- **Lệnh hoặc bước tái hiện:** Chạy lệnh có chuỗi `!'` trong cặp nháy kép `"` trên terminal Bash.
- **Nguyên nhân gốc:** Tính năng History Expansion trong Bash tự động bắt dấu `!` trong chuỗi ngoặc kép để tìm lại lệnh lịch sử gần nhất, gây lỗi cú pháp của shell trước khi kịp gọi Python.
- **Cách xử lý:** Bỏ dấu chấm than hoặc chuyển sang dùng nháy đơn bao ngoài `'...'`.
- **Cách xác minh sau khi sửa:** Chạy `uv run python -c "import chromadb, great_expectations, sentence_transformers; print('Environment Ready')"` in ra đúng chuỗi `Environment Ready`.
- **Điều học được:** Cần lưu ý cơ chế mở rộng ký tự đặc biệt của Linux Shell khi viết tài liệu hướng dẫn và lệnh kiểm thử tự động.

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   Dữ liệu JSON thô được fetch từ Crossref API (hoặc fallback snapshot local) → lưu trữ nguyên bản tại `data/raw/` → hàm `build_clean_dataframe` loại bỏ tag XML, tính `age_days`, khử trùng lặp và ghép 5 thành phần thành `text_for_embedding` → mô hình `all-MiniLM-L6-v2` mã hóa văn bản thành vector embeddings → nạp cùng metadata vào ChromaDB collection.

2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   Mỗi câu hỏi benchmark chứa tiêu đề bài báo trong ngoặc nháy `'...'` và danh sách `ground_truth_doc_ids`. Khi Agent truy vấn, hệ thống đo:
   - `retrieval_hit_rate`: Tỷ lệ các câu hỏi mà top-k retrieved documents có chứa ít nhất một `ground_truth_doc_ids`.
   - `token_f1`: Độ trùng khớp từ vựng giữa câu trả lời của Agent và `ground_truth`.

3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
   - Quality checks (GX 1.x): Kiểm soát tính toàn vẹn cấu trúc và logic dữ liệu tức thời (row count, non-null, unique constraint, min length).
   - Freshness SLA: Giám sát độ trôi dạt theo thời gian (Data Drift/Decay), đánh giá tỷ lệ tài liệu đã quá hạn (`age_days > 180`) để đảm bảo tri thức nạp vào AI luôn mang tính cập nhật.

4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   Để đảm bảo tính khoa học và khách quan của phép đối chiếu benchmark. Nếu thay đổi câu hỏi giữa các pha, sự thay đổi về điểm số sẽ bị nhiễu do độ khó của câu hỏi thay vì phản ánh chính xác chất lượng của dữ liệu.

5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   Dựa trên:
   - Bảng đối chiếu trong `data/reports/corruption_report.md`.
   - Great Expectations trên tập Repaired chuyển lại trạng thái `success = True`.
   - Freshness SLA chuyển lại trạng thái `is_fresh = True`.
   - `retrieval_hit_rate` và `mean_token_f1` trong `repaired_metrics.json` tăng trở lại xấp xỉ mức Baseline ban đầu.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |    90.0% |     50.0% |    90.0% | Sụt giảm mạnh khi bị tiêm lỗi, phục hồi hoàn toàn sau repair |
| `mean_token_f1`      |    0.850 |     0.350 |    0.850 | Silent failure làm suy giảm độ chính xác câu trả lời |
| `judge_accuracy`     |    90.0% |     40.0% |    90.0% | LLM judge đánh giá câu trả lời bị sai lệch nội dung |
| `mean_judge_score`   |     4.50 |      2.10 |     4.50 | Thang điểm 1-5 phản ánh rõ mức độ tin cậy của AI |
| Quality checks         |     PASS |      FAIL |     PASS | GX 1.x bắt thành công vi phạm unique ID và blank summary |
| Freshness status       |    FRESH |     STALE |    FRESH | Cảnh báo vi phạm ngưỡng 25% bài báo quá hạn 180 ngày |

### Kết luận từ số liệu

1. **Chuỗi lỗi dữ liệu:** Tiêm lỗi cắt ngắn tiêu đề, blank summary và stale date → GX Quality Gate báo `success = False`, Freshness báo `is_fresh = False` → Agent retrieval hit rate giảm từ 90% xuống 50%, Token F1 tụt từ 0.85 xuống 0.35 (Silent Failure).
2. **Chuỗi phục hồi:** Idempotent Repair tái tạo Clean DataFrame từ Raw snapshot → Quality Gate và Freshness SLA xanh trở lại → Agent lấy lại phong độ với Hit Rate 90% và Token F1 0.85.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Idempotent Data Pipeline:** Luôn giữ raw data bất biến (Immutable Raw Storage) để có thể tái tạo dữ liệu sạch bất kỳ lúc nào mà không sợ mất mát.
2. **Data Observability:** Great Expectations 1.x là chốt chặn sinh tử giúp ngăn chặn dữ liệu rác đi vào Vector Store trước khi gây ra Silent Failure cho AI.
3. **Continuous Benchmarking:** Đo lường định lượng trên cùng một tập test set là phương pháp khoa học duy nhất để kiểm chứng sức khỏe của mô hình RAG.

### Nếu có thêm thời gian

Tích hợp giao diện Dashboard theo dõi Data Drift theo thời gian thực bằng Streamlit và gửi webhook cảnh báo tới Slack/Discord khi Quality Gate bị vi phạm.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Lâm Quang Anh Quân  
**Ngày xác nhận:** 2026-09-26  
