# Deployment Information

## Public URL
https://your-agent.railway.app (Thay thế bằng URL thực tế sau khi deploy)

## Platform
Railway (hoặc Render / GCP Cloud Run)

## Test Commands

### 1. Health Check
```bash
curl https://your-agent.railway.app/health
# Expected Response: {"status": "ok", ...}
```

### 2. Readiness Check
```bash
curl https://your-agent.railway.app/ready
# Expected Response: {"ready": true, ...}
```

### 3. API Test (Requires Authentication)
* **Thử nghiệm không truyền API Key (Mong đợi lỗi 401):**
```bash
curl -X POST https://your-agent.railway.app/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello"}'
```

* **Thử nghiệm truyền API Key hợp lệ (Mong đợi kết quả 200 từ AI Agent):**
```bash
curl -X POST https://your-agent.railway.app/ask \
  -H "X-API-Key: your-secret-key" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is deployment?"}'
```

### 4. Rate Limiting Test (Mong đợi lỗi 429 sau khi vượt ngưỡng):
Chạy lệnh lặp gọi liên tiếp:
```bash
for i in {1..15}; do 
  curl -X POST https://your-agent.railway.app/ask \
    -H "X-API-Key: your-secret-key" \
    -H "Content-Type: application/json" \
    -d '{"question": "Hello '"$i"'"}'
  echo ""
done
```

## Environment Variables Set
- `PORT`: Cổng mạng chạy dịch vụ (mặc định Railway/Render tự gán)
- `ENVIRONMENT`: Thiết lập là `production`
- `AGENT_API_KEY`: API key bảo mật dùng để xác thực các request
- `REDIS_URL`: Địa chỉ kết nối đến cơ sở dữ liệu Redis dùng cho stateless session & security (ví dụ: `redis://default:password@host:port`)
- `DAILY_BUDGET_USD`: Giới hạn chi phí hàng ngày (ví dụ: `10.0`)
- `RATE_LIMIT_PER_MINUTE`: Tần suất truy cập tối đa (ví dụ: `10`)

## Screenshots
Vui lòng lưu các ảnh chụp màn hình tương ứng vào thư mục `screenshots/` và liên kết ở đây:
- [Deployment Dashboard](screenshots/dashboard.png)
- [Service Running Logs](screenshots/running.png)
- [Local/Cloud API Test Results](screenshots/test.png)
