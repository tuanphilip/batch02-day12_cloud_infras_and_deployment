# 📋 Danh sách Task - Day 12: Cloud Infrastructure & Deployment

Dưới đây là toàn bộ danh sách nhiệm vụ bạn cần hoàn thành cho bài lab này. Bạn có thể đánh dấu `[x]` khi hoàn thành xong mỗi nhiệm vụ.

---

## 🔍 Phần 1: Trả lời câu hỏi lý thuyết và bài tập thực hành (Part 1 - Part 5)
Bạn cần tạo một file `MISSION_ANSWERS.md` ở thư mục gốc để ghi lại câu trả lời cho các bài tập dưới đây.

### 🏁 Part 1: Localhost vs Production (30 phút)
- [x] **Exercise 1.1: Phát hiện Anti-patterns**
  - Đọc code `01-localhost-vs-production/develop/app.py`
  - Liệt kê ít nhất 5 vấn đề chưa tối ưu cho production (Hardcoded API key, cố định Port, Debug mode, thiếu Health check, thiếu Graceful shutdown) vào `MISSION_ANSWERS.md`.
- [x] **Exercise 1.2: Chạy thử phiên bản Basic**
  - Chạy môi trường local và kiểm tra hoạt động cơ bản của API.
- [x] **Exercise 1.3: So sánh phiên bản Advanced**
  - Chạy `01-localhost-vs-production/production/app.py`.
  - Hoàn thiện bảng so sánh chi tiết giữa phiên bản Basic và Advanced vào `MISSION_ANSWERS.md` (Giải thích tại sao Config management, Health checks, Structured logging, và Graceful shutdown lại quan trọng).

### 🐳 Part 2: Docker Containerization (45 phút)
- [x] **Exercise 2.1: Tìm hiểu Dockerfile cơ bản**
  - Đọc `02-docker/develop/Dockerfile`.
  - Trả lời các câu hỏi về: Base image, working directory, lý do copy `requirements.txt` trước, và sự khác nhau giữa `CMD` và `ENTRYPOINT` vào `MISSION_ANSWERS.md`.
- [x] **Exercise 2.2: Build và Run Container cơ bản**
  - Build image `my-agent:develop` và chạy thử.
  - Đo dung lượng của image vừa build (bằng lệnh `docker images`) và ghi lại số MB vào `MISSION_ANSWERS.md`.
- [x] **Exercise 2.3: Multi-stage Build**
  - Đọc `02-docker/production/Dockerfile` và tìm hiểu vai trò của Stage 1 (Builder) và Stage 2 (Runtime).
  - Build image `my-agent:advanced` và so sánh dung lượng giảm bao nhiêu % so với bản develop. Ghi kết quả vào `MISSION_ANSWERS.md`.
- [x] **Exercise 2.4: Docker Compose Stack**
  - Đọc hiểu tệp `docker-compose.yml` (Nginx LB + 3 Agent instances + Redis).
  - Vẽ sơ đồ kiến trúc truyền thông (Architecture diagram) giữa các thành phần và thêm vào `MISSION_ANSWERS.md`.
  - Khởi động stack bằng `docker compose up --scale agent=3` và thử nghiệm gọi API qua cổng `80` (Nginx).

### ☁️ Part 3: Cloud Deployment (45 phút)
- [ ] **Exercise 3.1: Deploy Railway**
  - Cài đặt Railway CLI (`npm i -g @railway/cli`) và đăng nhập (`railway login`).
  - Khởi tạo project, thiết lập các biến môi trường (`PORT`, `AGENT_API_KEY`), và triển khai lên Railway (`railway up`).
  - Ghi nhận URL public hoạt động vào `DEPLOYMENT.md` và `MISSION_ANSWERS.md`.
- [x] **Exercise 3.2: So sánh Render & Railway**
  - So sánh file cấu hình `render.yaml` và `railway.toml`. Nêu sự khác nhau và ghi vào `MISSION_ANSWERS.md`.
- [x] **Exercise 3.3 (Tùy chọn): CI/CD với GCP Cloud Run**
  - Đọc hiểu cách hoạt động của `cloudbuild.yaml` và `service.yaml`.

### 🛡️ Part 4: API Security (40 phút)
- [x] **Exercise 4.1: API Key Authentication**
  - Xem cơ chế kiểm tra API Key tại `04-api-gateway/develop/app.py`. Trả lời các câu hỏi trong `MISSION_ANSWERS.md`.
- [x] **Exercise 4.2: JWT Authentication**
  - Đọc hiểu JWT flow tại `04-api-gateway/production/auth.py`. Chạy thử để lấy token và dùng token gọi API, ghi nhận kết quả.
- [x] **Exercise 4.3: Rate Limiting**
  - Đọc thuật toán rate limiter trong `rate_limiter.py`. Thử nghiệm gọi 20 requests liên tiếp để kích hoạt lỗi `429 Too Many Requests`. Ghi nhận kết quả test.
- [x] **Exercise 4.4: Cost Guard với Redis**
  - Hoàn thiện logic hàm `check_budget` trong `04-api-gateway/production/cost_guard.py` để giới hạn ngân sách người dùng ($10/tháng) và lưu trữ dữ liệu chi phí vào Redis.
  - Ghi chú giải thích giải pháp của bạn vào `MISSION_ANSWERS.md`.
 
 ### ⚡ Part 5: Scaling & Reliability (40 phút)
- [x] **Exercise 5.1: Health & Readiness Checks**
  - Hoàn thiện 2 endpoints `/health` (liveness probe) và `/ready` (readiness probe) trong `05-scaling-reliability/develop/app.py` để kiểm tra kết nối database/Redis.
  - Chạy thử, giải thích giải pháp và ghi nhận kết quả test vào `MISSION_ANSWERS.md`.
- [x] **Exercise 5.2: Graceful Shutdown**
  - Hoàn thiện hàm xử lý tín hiệu `SIGTERM` trong `05-scaling-reliability/develop/app.py`. Thử nghiệm gửi request và kill tiến trình để kiểm tra request hiện tại có được xử lý xong trước khi thoát không. Ghi nhận kết quả.
- [x] **Exercise 5.3: Refactor thành Stateless**
  - Thay đổi cách lưu lịch sử trò chuyện trong `05-scaling-reliability/production/app.py` từ bộ nhớ trong (in-memory) sang Redis.
- [x] **Exercise 5.4: Test Load Balancing**
  - Chạy stack Docker Compose với 3 instances agent và kiểm tra log phân tán request của Nginx.
- [x] **Exercise 5.5: Test Stateless**
  - Chạy script `test_stateless.py`, thực hiện kill ngẫu nhiên instance agent đang chạy và đảm bảo cuộc trò chuyện vẫn tiếp diễn mà không mất lịch sử nhờ có Redis.

---

## 🏗️ Phần 2: Dự án cuối khóa - Production-Ready AI Agent (Part 6)
Hoàn thiện dự án tại thư mục `06-lab-complete/` đáp ứng đầy đủ các tiêu chuẩn sau:

### ⚙️ Tính năng hệ thống (Functional & Non-Functional)
- [x] **Hoạt động ổn định**: Trả lời câu hỏi đúng qua REST API (`POST /ask`).
- [x] **Quản lý hội thoại**: Lưu lịch sử hội thoại (conversation history) để duy trì ngữ cảnh.
- [x] **12-Factor Config**: Quản lý toàn bộ cấu hình qua biến môi trường thông qua Pydantic (`app/config.py`).
- [x] **Structured Logging**: Ghi log có cấu trúc dạng JSON (`json.dumps`).
- [x] **API Key Authentication**: Xác thực quyền truy cập trước khi cho phép gọi API.
- [x] **Rate Limiting (Stateless)**: Giới hạn 10 requests/phút cho mỗi user, lưu trạng thái trong Redis.
- [x] **Cost Guard (Stateless)**: Giới hạn budget $10/tháng cho mỗi user, tính toán dựa trên token input/output và lưu trạng thái trong Redis.
- [x] **Health Checks**: Đầy đủ 2 endpoint `/health` và `/ready`.
- [x] **Graceful Shutdown**: Xử lý tín hiệu `SIGTERM` dọn dẹp các kết nối và đợi request hoàn thành.
- [x] **Dockerization**: Viết Dockerfile tối ưu (Multi-stage, slim image, kích thước < 500 MB, chạy dưới quyền user non-root `agent`, cấu hình `HEALTHCHECK` trong Dockerfile).
- [x] **Docker Compose**: Tệp `docker-compose.yml` khởi chạy cả dịch vụ agent và Redis với cơ chế kiểm tra trạng thái sức khỏe (`depends_on service_healthy`).
- [ ] **Deploy Cloud**: Đưa lên nền tảng Railway hoặc Render thành công và có public URL hoạt động.

### 🧪 Đảm bảo chất lượng (Verification)
- [x] **Kiểm tra tự động**: Chạy file test `python -X utf8 check_production_ready.py` trong thư mục `06-lab-complete` và đạt **100% check pass (20/20)**.

---

## 📤 Hồ sơ nộp bài (Deliverables)
Đảm bảo repository GitHub của bạn chứa đầy đủ các tệp tin sau:
- [x] **Mã nguồn đầy đủ**: Toàn bộ mã nguồn đã hoàn thiện trong thư mục `06-lab-complete/`.
- [x] **`MISSION_ANSWERS.md`**: Đầy đủ câu trả lời cho các Exercise từ Part 1 đến Part 5.
- [x] **`DEPLOYMENT.md`**: Chứa thông tin public URL hoạt động, nền tảng deploy, các lệnh test `curl` cụ thể cho health check và hỏi agent (kèm API key), danh sách biến môi trường đã set.
- [ ] **`screenshots/`**: Thư mục chứa các ảnh chụp chứng minh hoạt động:
  - `screenshots/dashboard.png` (Quản lý dịch vụ trên cloud)
  - `screenshots/running.png` (Dịch vụ đang chạy bình thường)
  - `screenshots/test.png` (Kết quả chạy thử API qua curl hoặc Postman)
- [ ] **Clean Git History**: Đẩy code lên GitHub công khai (hoặc cấp quyền cho giảng viên), đảm bảo không commit file `.env` chứa secret.

---
**📅 Hạn nộp bài:** Trước ngày 17/04/2026. Chúc bạn làm bài tốt! 💪
