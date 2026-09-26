# Danh Sách Thành Viên & Báo Cáo Phân Công Nhóm

- **Tên Nhóm:** `promaxima`
- **Mã Nhóm / Lớp:** `K4-L3B-DAY10`
- **Tên Repository Nộp Bài:** `K4-L3B-DAY10-promaxima-DataPipelineDataObservability`

---

## Thành viên

| STT | Họ và tên | MSSV | Email | Vai trò & Phân công công việc | Báo cáo cá nhân |
|---:|---|---|---|---|---|
| 1 | Lâm Quang Anh Quân | 2A202602467 | quanlam0105@gmail.com | Trưởng nhóm / Pipeline Integrator & Data Recovery (`core/`, `phase1.py`, `corruption_flow.py`) | `report/2A202602467_LamQuangAnhQuan.md` |
| 2 | Nguyễn Văn Diện | 2A202602615 | diendls321@gmail.com | Data Foundation & RAG Vector Index (`crossref.py`, `cleaning.py`, `retrieval/index.py`, ChromaDB) | `report/2A202602615_NguyenVanDien.md` |
| 3 | Bùi Văn Quang | 2A202602688 | quangvanbui2004@gmail.com | Observability & Evaluation (`quality.py` GX 1.x, `testset.py`, reporting) | `report/2A202602688_BuiVanQuang.md` |

*(Nếu nhóm có 3 hoặc 5-6 thành viên, xem bảng phân công chi tiết theo vai trò trong file `CHECKPOINTS.md`)*.

---

## Cá nhân

### Lâm Quang Anh Quân - 2A202602467
- **Vai trò:** Trưởng nhóm, Điều phối Pipeline & Phục hồi dữ liệu.
- **Công việc chi tiết đã hoàn thành:**
  - Thiết lập cấu hình hệ thống `core/config.py` và đường dẫn artifacts `core/utils.py`.
  - Kết nối luồng thực thi trong `src/pipelines/phase1.py` và `src/pipelines/corruption_flow.py`.
  - Thực thi cơ chế Idempotent Repair phục hồi dữ liệu từ raw snapshot.
  - Kiểm tra tính nhất quán của các artifacts và theo dõi Contributor tracking trên GitHub nhánh `main`.
- **Điều học được / Đóng góp chính:**
  - Hiểu sâu sắc về thiết kế Idempotent Pipeline và quản lý trạng thái luồng dữ liệu đa tầng.

### Nguyễn Văn Diện - 2A202602615
- **Vai trò:** Phụ trách Ingestion, Làm sạch dữ liệu & RAG Vector Database.
- **Công việc chi tiết đã hoàn thành:**
  - Xây dựng module thu thập Crossref API với cơ chế Fallback offline trong `src/ingestion/crossref.py`.
  - Chuẩn hóa schema, tính toán trường `age_days` và `text_for_embedding` trong `src/ingestion/cleaning.py`.
  - Quản lý mô hình embedding `sentence-transformers/all-MiniLM-L6-v2`.
  - Nạp và quản lý 3 collection riêng biệt trong ChromaDB (`papers-baseline`, `papers-corrupted`, `papers-repaired`).
  - Xây dựng QA Agent truy vấn ngữ cảnh chính xác theo tài liệu trong `src/retrieval/index.py`.
- **Điều học được / Đóng góp chính:**
  - Kỹ thuật truy vết nguồn gốc dữ liệu (Data Lineage), bảo toàn raw snapshot trước khi biến đổi và cô lập các không gian vector để so sánh khách quan giữa dữ liệu sạch và dữ liệu bị lỗi.

### Bùi Văn Quang - 2A202602688
- **Vai trò:** Phụ trách Data Observability & Benchmark Evaluation.
- **Công việc chi tiết đã hoàn thành:**
  - Thiết lập Quality Gate theo chuẩn mới **Great Expectations 1.x** và giám sát Freshness SLA trong `src/observability/quality.py`.
  - Xây dựng bộ câu hỏi đánh giá chuẩn trong `src/evaluation/testset.py`.
  - Đo lường và xuất bảng đối chiếu 3 trạng thái vào `data/reports/corruption_report.md`.
- **Điều học được / Đóng góp chính:**
  - Cách thiết lập hệ thống cảnh báo sớm chặn đứng hiện tượng Silent Failure trước khi dữ liệu vào serving layer.
