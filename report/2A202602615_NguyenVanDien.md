# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Nguyễn Văn Diện            |
| MSSV               | 2A202602615                |
| Khóa/Lớp         | K4-L3B-DAY10               |
| Tên nhóm         | promaxima                  |
| Vai trò chính    | Data Foundation & RAG Vector Index (`crossref.py`, `cleaning.py`, `retrieval/index.py`, ChromaDB, `corruption.py`) |
| Repository         | https://github.com/awun0105/K4-L3B-DAY10-promaxima-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26                 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Thu thập & Phân tích Crossref API | `src/ingestion/crossref.py` | Crossref REST API / Local snapshot | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Hoàn thành |
| Làm sạch dữ liệu & Pre-embed | `src/ingestion/cleaning.py` | `PaperRecord` raw list | `data/clean/papers_clean.csv`, `data/clean/papers_clean.json` | Hoàn thành |
| Vector Indexing & Embeddings | `src/retrieval/embeddings.py`, `src/retrieval/index.py` | Clean Dataframe | ChromaDB collections (`papers-baseline`, `papers-corrupted`, `papers-repaired`) | Hoàn thành |
| Giả lập lỗi dữ liệu (Corruption Suite) | `src/ingestion/corruption.py` | Clean DataFrame | `data/results/corruption_log.json`, `data/clean/papers_clean_corrupted.*` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Thống nhất Schema Data Contract      | Lâm Quang Anh Quân (Pipeline)        | Đồng bộ 14 trường dữ liệu chuẩn giữa Ingestion, Cleaning và Great Expectations |
| Cung cấp corrupt hooks cho GX        | Bùi Văn Quang (Observability)        | Thiết lập đúng các trường `summary` rỗng và ID trùng để GX bắt lỗi chính xác |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Xây dựng Ingestion & Fallback snapshot | `src/ingestion/crossref.py` | Raw JSON records | Tải đủ 24 bài báo và lưu raw artifacts |
| Data Cleaning & chuẩn hóa schema | `src/ingestion/cleaning.py` | Cleaned dataframe 24 dòng | Khử trùng lặp, tính `age_days`, tạo `text_for_embedding` |
| Quản lý Embeddings & ChromaDB Collections | `src/retrieval/index.py` | Vector store indexed | ChromaDB collection nạp 24 docs |
| Triển khai Synthetic Data Corruption Suite | `src/ingestion/corruption.py` | `corruption_log.json` & corrupted data | Tiêm đủ 6 dạng lỗi dữ liệu thực tế và ghi nhận log |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

File `data/clean/papers_clean.json` (24 bài báo) chứa đầy đủ 14 thuộc tính chuẩn và trường `text_for_embedding` gồm 5 phần định dạng chuẩn hóa, làm đầu vào tin cậy cho mô hình nhúng `all-MiniLM-L6-v2` và cơ sở dữ liệu vector ChromaDB. Đồng thời suite tiêm lỗi `corruption.py` ghi nhận đầy đủ 6 kịch bản lỗi vào `data/results/corruption_log.json`.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Dữ liệu học thuật từ API bên ngoài (Crossref) có nhiều biến thể bất thường: chứa các thẻ định dạng JATS/XML (`<jats:p>`, `<jats:title>`), cấu trúc ngày không đồng nhất (`date-parts`), thiếu abstract hoặc rỗng summary. Nếu đưa trực tiếp vào mô hình nhúng và vector store, các tạp âm này sẽ làm sai lệch phân bố embedding và gây ra lỗi truy xuất cho Agent RAG.

### Cách triển khai

1. **Robust Ingestion with Fallback:** Xây dựng hàm `fetch_source_records()` với cơ chế retry bằng `tenacity`. Khi gặp lỗi mạng hoặc API rate limit, tự động fallback an toàn sang snapshot cục bộ `data/raw/crossref_response.json` để pipeline luôn tất định.
2. **Text Cleaning & Formatting:** Dùng regex loại bỏ triệt để các thẻ HTML/XML, chuẩn hóa khoảng trắng thừa, sinh `text_for_embedding` theo cấu trúc 5 khối:
   ```text
   Title: ...
   Authors: ...
   Published: ...
   Categories: ...
   Summary: ...
   ```
3. **Synthetic Corruption:** Thiết kế 6 hàm tiêm lỗi: drop latest (20%), blank summary, inject noise, truncate title, stale date (lùi 5 năm), và duplicate rows để mô phỏng lỗi thực tế trong data engineering.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | Crossref API payload / Local JSON snapshot  |
| Output                         | Clean dataframe & Vector Store collections  |
| Module phụ thuộc             | `core/config.py`                            |
| Module sử dụng output        | `observability`, `evaluation`, `pipelines`  |
| Điều kiện lỗi cần xử lý | Lỗi mạng, 429 rate limit, schema missing    |

### Cách xác minh

```bash
uv run python -c "from core.config import load_settings; from ingestion.crossref import fetch_source_records; s=load_settings(); r=fetch_source_records(s); print(f'Đã tải {len(r)} bài báo')"
uv run python -c "from datetime import datetime, timezone; from core.config import load_settings; from ingestion.crossref import load_raw_records; from ingestion.cleaning import build_clean_dataframe; s=load_settings(); df=build_clean_dataframe(load_raw_records(s.paths.raw_records_json), datetime.now(timezone.utc)); print(f'Clean thành công {len(df)} dòng')"
```

- **Kết quả mong đợi:** Tải đủ 24 records và clean thành công 24 dòng với trường `text_for_embedding` hoàn chỉnh.
- **Kết quả thực tế:** Hệ thống tải đủ 24 records, làm sạch 24 dòng không có lỗi null và cấu trúc `text_for_embedding` đạt chuẩn.
- **Artifact/log:** `data/raw/crossref_records.json`, `data/clean/papers_clean.json`

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn cách xây dựng trường văn bản phục vụ Embedding (`text_for_embedding`).
- **Các phương án đã cân nhắc:**
  - *Phương án A:* Chỉ dùng trường `summary` (hoặc `abstract`) làm embedding text.
  - *Phương án B:* Ghép tổng hợp 5 trường: `Title`, `Authors`, `Published`, `Categories`, `Summary`.
- **Phương án đã chọn:** Phương án B.
- **Lý do:** Khi người dùng truy vấn tài liệu khoa học, họ thường hỏi kèm theo ngữ cảnh thực thể (tên tác giả, năm công bố, danh mục chuyên ngành). Việc ghép cả 5 thành phần giúp vector embedding đại diện được toàn bộ không gian ngữ nghĩa và metadata của bài báo.
- **Bằng chứng quyết định phù hợp:** `retrieval_hit_rate` của Baseline pipeline đạt tuyệt đối 1.0000 (10/10 câu hỏi test tìm thấy đúng document liên quan).

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Abstract bài báo trả về từ Crossref chứa các thẻ XML học thuật dạng `<jats:p>Background: ...</jats:p>` và `<jats:italic>`, làm nhiễu token của câu tóm tắt.
- **Lệnh hoặc bước tái hiện:** Kiểm tra nội dung trường `abstract` sau khi parse từ `crossref_response.json`.
- **Nguyên nhân gốc:** Crossref lưu trữ abstract theo chuẩn JATS XML specification thay vì plain text.
- **Cách xử lý:** Bổ sung bước làm sạch tiền xử lý bằng regex `re.sub(r"<[^>]+>", "", text)` kết hợp `html.unescape()` để loại bỏ toàn bộ các thẻ XML và chuyển đổi ký tự mã hóa về văn bản thô chuẩn.
- **Cách xác minh sau khi sửa:** Chạy kiểm tra không còn bản ghi nào trong `papers_clean.json` chứa ký tự `<jats:` hoặc thẻ HTML.
- **Điều học được:** Không bao giờ tin tưởng dữ liệu từ API bên ngoài là văn bản thuần mà luôn cần sanitization kỹ lưỡng.

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   Dữ liệu JSON thô được tải từ Crossref API (hoặc fallback snapshot) → lưu tại `data/raw/` → hàm `build_clean_dataframe()` xử lý làm sạch và tạo `text_for_embedding` → SentenceTransformer mã hóa thành vectors 384 chiều → lưu trữ và đánh chỉ mục trong ChromaDB PersistentClient.

2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   Mỗi câu test có một hoặc nhiều `ground_truth_doc_ids`. Khi agent truy xuất top-3 văn bản, hệ thống kiểm tra xem có ID ground-truth trong top-3 không để tính `retrieval_hit_rate`, đồng thời so sánh câu trả lời sinh ra với ground truth để tính `mean_token_f1` và điểm số LLM Judge.

3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
   - Quality checks (Great Expectations): Kiểm tra tính toàn vẹn cấu trúc và logic tại một thời điểm (schema, non-null, unique ID, min length).
   - Freshness SLA: Theo dõi độ trôi dạt và tính cập nhật theo thời gian (tỷ lệ bài báo quá hạn 180 ngày).

4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   Để giữ biến kiểm soát độc lập (Controlled Variable). Nếu đổi test set, sự thay đổi điểm số có thể do độ khó của câu hỏi chứ không phản ánh đúng ảnh hưởng của sự suy giảm hoặc phục hồi dữ liệu.

5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   Dựa trên Great Expectations đạt `success=True`, Freshness SLA đạt `is_fresh=True`, `retrieval_hit_rate = 1.0000` và `mean_token_f1` khôi phục về mức baseline 0.7076 trong `repaired_metrics.json`.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |   1.0000 |    1.0000 |   1.0000 | Top_k=3 vẫn tìm thấy tài liệu nhờ độ phủ của vector search |
| `mean_token_f1`      |   0.7076 |    0.5611 |   0.7076 | **Silent Failure:** F1 tụt 0.1465 khi summary bị xóa/nhiễu, phục hồi 100% sau repair |
| `judge_accuracy`     |   0.5000 |    0.6000 |   0.8000 | LLM judge đánh giá theo schema ngữ nghĩa nghiêm ngặt; bản repaired đạt độ chính xác cao nhất (80%) |
| `mean_judge_score`   |   3.4000 |    3.2000 |   3.6000 | Điểm trung bình đánh giá chất lượng câu trả lời giảm khi bị tiêm lỗi và tăng sau khi sửa |
| Quality checks         |     PASS |      FAIL |     PASS | GX 1.x bắt thành công vi phạm unique ID (4 unexpected) và blank summary (2 bản ghi) |
| Freshness status       |    FRESH |     STALE |    FRESH | Cảnh báo vi phạm ngưỡng 25% bài báo quá hạn 180 ngày (tỷ lệ cũ vọt lên 31.82%) |

### Kết luận từ số liệu

1. **[Data corruption (blank summary + noise injection)] → [Great Expectations Quality Gate bắt lỗi vi phạm và báo FAIL] → [Agent bị Silent Failure khi Token F1 giảm từ 0.7076 xuống 0.5611].**
2. **[Idempotent Repair từ raw snapshot] → [Great Expectations và Freshness SLA xanh trở lại (PASS/FRESH)] → [Agent phục hồi hoàn toàn Token F1 về 0.7076 và Judge Score đạt 3.60].**

**Corruption nào ảnh hưởng rõ nhất và vì sao?**
Lỗi `blank_summary` và `inject_noise` ảnh hưởng rõ nhất đến RAG Agent vì làm mất hoàn toàn nội dung ngữ nghĩa hoặc đưa tạp âm vào context cung cấp cho LLM, khiến câu trả lời bị sai lệch dù retrieval vẫn hit.

**Kết quả nào khác với kỳ vọng ban đầu?**
`retrieval_hit_rate` vẫn giữ mức 1.0000 ngay cả khi bị tiêm lỗi truncate title. Giả thuyết là do `top_k=3` kết hợp với thông tin tác giả và danh mục trong `text_for_embedding` vẫn đủ để vector similarity định vị đúng tài liệu.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Immutable Raw Data:** Lưu trữ dữ liệu thô nguyên bản là điều kiện tiên quyết để thực hiện Idempotent Repair thành công.
2. **Data Sanitization:** Tiền xử lý và làm sạch dữ liệu kỹ lưỡng (loại bỏ XML tags, chuẩn hóa format) quyết định trực tiếp chất lượng embedding.
3. **Silent Failure in RAG:** Dữ liệu bẩn không làm hệ thống sập nhưng làm suy giảm chất lượng câu trả lời âm thầm, chỉ có Observability và Quantitative Benchmarking mới phát hiện được.

### Nếu có thêm thời gian

Xây dựng bộ Data Validator tự động kiểm tra định dạng và cấu trúc abstract ngay ở bước Ingestion trước khi đưa vào DataFrame.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Văn Diện  
**Ngày xác nhận:** 2026-09-26  
