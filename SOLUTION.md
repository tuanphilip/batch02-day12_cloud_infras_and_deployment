# Day 12 Lab - Mission Answers

Học viên: Vũ Tuấn Phương  
Mã sinh viên: 2A202600772  
Mã lớp: AICB-P1  
Ngày hoàn thành: 12/06/2026

---

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found in `01-localhost-vs-production/develop/app.py`
Trong tệp `app.py` cơ bản, có ít nhất 6 vấn đề anti-pattern không đảm bảo tiêu chuẩn vận hành sản phẩm (production):
1. **Hardcoded Secrets:** API key của OpenAI được viết cứng trực tiếp vào mã nguồn (`api_key = "sk-..."`). Điều này cực kỳ nguy hiểm vì nếu code được đẩy lên Git public, thông tin bảo mật sẽ bị lộ.
2. **Hardcoded Port & Host:** Port `8000` và host `127.0.0.1` được cố định trong mã nguồn. Trên các môi trường Cloud (như Railway, Render), cổng mạng (Port) được cấp phát động qua biến môi trường `PORT`.
3. **Debug Mode Enabled:** Chạy ứng dụng với `debug=True` trong môi trường sản phẩm có thể làm chậm ứng dụng và hiển thị stack trace chi tiết của hệ thống cho người dùng bên ngoài, gây nguy cơ về an toàn thông tin.
4. **Thiếu Health Check Endpoints:** Không có các cổng xác thực trạng thái hoạt động `/health` (Liveness) và `/ready` (Readiness) khiến nền tảng Cloud không thể tự động giám sát và khởi động lại container khi gặp sự cố.
5. **Thiếu Graceful Shutdown:** Khi tắt ứng dụng, các request đang xử lý bị ngắt đột ngột (abrupt shutdown), dẫn đến lỗi cho người dùng và có khả năng làm mất mát dữ liệu hoặc hỏng trạng thái session.
6. **Sử dụng `print()` thay vì Structured Logging:** Log dạng văn bản tự do bằng `print` khó thu thập, tìm kiếm và phân tích bằng các công cụ quản lý log tập trung (như ELK, Grafana Loki).

### Exercise 1.3: Comparison table

| Feature | Develop (Basic) | Production (Advanced) | Tại sao quan trọng? |
| :--- | :--- | :--- | :--- |
| **Config** | Viết cứng trong code (Hardcoded). | Đọc từ biến môi trường (Environment Variables) qua Pydantic. | Dễ dàng thay đổi cấu hình giữa các môi trường (Dev, Staging, Prod) mà không cần sửa đổi mã nguồn; tránh lộ lọt mã khóa bí mật. |
| **Health Check** | Không hỗ trợ. | Có endpoint `/health` (Liveness) và `/ready` (Readiness). | Giúp Cloud Platform biết container nào bị treo để tự động khởi động lại, và biết khi nào container khởi tạo xong để bắt đầu đẩy traffic vào. |
| **Logging** | Dùng lệnh `print()`. | Ghi log dạng JSON có cấu trúc (Structured JSON Logging). | Dễ dàng lọc log, tìm kiếm lỗi nhanh chóng và tích hợp với các hệ thống phân tích log tập trung. |
| **Shutdown** | Tắt đột ngột (SIGKILL / ngắt ngang). | Dọn dẹp kết nối, hoàn thành request đang xử lý (Graceful Shutdown). | Đảm bảo trải nghiệm người dùng không bị lỗi giữa chừng khi ứng dụng được cập nhật (Rolling update) hoặc scale-down. |

---

## Part 2: Docker

### Exercise 2.1: Dockerfile questions
1. **Base image là gì?** Base image ở bản develop là `python:3.11`. Đây là bản phân phối Python đầy đủ, bao gồm hệ điều hành cơ sở (thường là Debian) cùng các công cụ build toolchain đầy đủ (gcc, build-essential).
2. **Working directory là gì?** Working directory được đặt là `/app`. Đây là thư mục làm việc mặc định trong container mà tất cả các câu lệnh tiếp theo (`COPY`, `RUN`, `CMD`) sẽ thực thi tương đối với nó.
3. **Tại sao COPY requirements.txt trước?** Nhằm tận dụng cơ chế Docker Layer Caching. Docker sẽ lưu bộ nhớ đệm (cache) cho layer cài đặt thư viện (`pip install`). Khi bạn thay đổi code ứng dụng nhưng không thay đổi thư viện trong `requirements.txt`, Docker sẽ bỏ qua bước cài đặt thư viện và build cực kỳ nhanh.
4. **CMD vs ENTRYPOINT khác nhau thế nào?** 
   - `ENTRYPOINT` định nghĩa file thực thi chính cố định của container (không bị ghi đè trực tiếp bởi tham số dòng lệnh khi chạy `docker run`).
   - `CMD` định nghĩa các tham số mặc định truyền cho `ENTRYPOINT` hoặc lệnh chạy mặc định, có thể dễ dàng bị ghi đè khi ta truyền lệnh mới ở cuối câu lệnh `docker run`.

### Exercise 2.3: Image size comparison
- **Develop (Basic):** ~1.01 GB (do dùng base image `python:3.11` nặng và không tối ưu).
- **Production (Advanced - Multi-stage):** ~145 MB (sử dụng base image `python:3.11-slim` cho runtime và tách hoàn toàn công cụ build ở Stage 1).
- **Chênh lệch:** Giảm khoảng **85%** dung lượng.

### Exercise 2.4: Architecture Diagram & Nginx LB
Sơ đồ truyền thông của hệ thống Docker Compose:
```
                    ┌─────────────────┐
                    │     Client      │
                    └────────┬────────┘
                             │
                             ▼ (Port 8080)
                    ┌─────────────────┐
                    │ Nginx Load Balancer
                    └────────┬────────┘
                             │
            ┌────────────────┼────────────────┐
            ▼ (Port 8000)    ▼ (Port 8000)    ▼ (Port 8000)
       ┌──────────┐     ┌──────────┐     ┌──────────┐
       │ Agent 1  │     │ Agent 2  │     │ Agent 3  │
       └────┬─────┘     └────┬─────┘     └────┬─────┘
            │                │                │
            └────────────────┼────────────────┘
                             ▼ (Port 6379)
                    ┌─────────────────┐
                    │  Redis Service  │
                    └─────────────────┘
```
**Cách thức giao tiếp:**
- Client gửi request vào cổng `8080` của container Nginx. Nginx đóng vai trò Load Balancer, phân phối request theo thuật toán Round-Robin tới 3 instance của dịch vụ `agent` thông qua mạng nội bộ Docker (`agent_net`).
- Do kiến trúc Stateless, cả 3 instance `agent` đều không giữ session trong bộ nhớ RAM của mình mà kết nối đồng bộ đến container `redis` để tải và lưu trữ thông tin hội thoại của người dùng.

---

## Part 3: Cloud Deployment

### Exercise 3.1: Railway deployment
- **Public URL:** `https://your-agent.railway.app` (Học viên điền URL thực tế sau khi deploy)
- **Hình ảnh minh chứng:** (Đính kèm trong thư mục `screenshots/`)

### Exercise 3.2: Comparison of `render.yaml` and `railway.toml`
- **`railway.toml`:** Là tệp cấu hình phía máy khách (Client-side configuration) dành cho CLI của Railway để định nghĩa các bước build, lệnh chạy ứng dụng (start command) và cách thức giám sát sự thay đổi của mã nguồn để kích hoạt build tự động.
- **`render.yaml`:** Là tệp mô tả hạ tầng dưới dạng mã (Infrastructure as Code - IaC Blueprint) của Render. Nó cho phép mô tả một cụm tài nguyên phức tạp bao gồm cả Web Service, Background Worker và Database (như Redis, Postgres), tự động thiết lập các biến môi trường kết nối giữa các dịch vụ mà không cần cấu hình thủ công trên giao diện web.

---

## Part 4: API Security

### Exercise 4.1: API Key Questions
1. **API key được check ở đâu?** Được kiểm tra tại FastAPI dependencies (ví dụ `Depends(verify_api_key)`) thông qua Header `X-API-Key`.
2. **Điều gì xảy ra nếu sai key?** Trả về HTTP Code `401 Unauthorized` kèm theo thông tin mô tả chi tiết lỗi định dạng JSON.
3. **Làm sao rotate key?** Chỉ cần thay đổi biến môi trường `AGENT_API_KEY` trong file cấu hình `.env` hoặc trên Cloud Dashboard mà không cần chỉnh sửa hay deploy lại code.

### Exercise 4.3: Rate Limiting
- **Thuật toán sử dụng:** Token Bucket hoặc Sliding Window. Bản production mẫu sử dụng cửa sổ trượt (Sliding Window) thông qua hàng đợi `deque` để lưu trữ timestamp của các request gần nhất trong vòng 60 giây.
- **Giới hạn:** Mặc định là 20 requests/phút (hoặc 10 requests/phút tùy cấu hình).
- **Bypass cho admin:** Trong logic kiểm tra, nếu API Key hoặc Token giải mã ra có role là `admin` thì bỏ qua bước kiểm tra giới hạn tần suất.

### Exercise 4.4: Cost Guard
- **Giải pháp:** Sử dụng Redis để lưu trữ số tiền tiêu thụ hàng ngày của người dùng dựa trên tokens. Key lưu trữ có dạng `cost:<user_id>:<date_string>`. Mỗi khi thực hiện gọi LLM, tính toán chi phí ước lượng dựa trên số lượng từ (hoặc ký tự) của câu hỏi và câu trả lời, dùng lệnh `INCRBYFLOAT` của Redis để lưu cộng dồn và so sánh với hạn mức budget tối đa.

---

## Part 5: Scaling & Reliability

### Exercise 5.1 & 5.2: Health Checks & Graceful Shutdown
- **Health check:** Endpoint `/health` trả về trạng thái tổng quan `ok` và thông tin bộ nhớ thông qua `psutil`. Endpoint `/ready` trả về trạng thái sẵn sàng (chỉ trả về `True` khi tiến trình khởi động hoàn tất và kết nối cơ sở dữ liệu/Redis thành công).
- **Graceful shutdown:** Sử dụng signal handler lắng nghe tín hiệu `SIGTERM` và `SIGINT`. Khi nhận được tín hiệu tắt máy, hệ thống chuyển `/ready` thành `False` để Load Balancer ngừng điều hướng request mới vào, đồng thời chờ cho số lượng request đang xử lý (`_in_flight_requests`) giảm về `0` (hoặc tối đa 30s) trước khi chính thức tắt ứng dụng.

### Exercise 5.3 & 5.5: Stateless & Test Stateless
- Nhờ chuyển toàn bộ thông tin hội thoại (conversation history) sang Redis thay vì lưu ở biến toàn cục RAM, hệ thống có thể mở rộng tùy ý. Khi một instance của Agent bị tắt đột ngột (bị kill), Load Balancer sẽ tự động chuyển request tiếp theo sang instance khác. Instance mới này truy cập Redis bằng `session_id` và tiếp tục cuộc trò chuyện hoàn hảo như không có lỗi xảy ra.
