# 📩 Notification Service (`notification_service.py`)

## Mục đích
Gửi thông báo qua email và SMS cho bệnh nhân.

## Status: 🟡 Mock
Chỉ ghi log — cần tích hợp với Twilio (SMS), SendGrid/SES (email) khi deploy.

## API

| Method | Tham số | Chức năng |
|--------|---------|-----------|
| `send_email(to, subject, body, cc)` | Email + nội dung | Gửi email |
| `send_sms(to, message)` | SĐT + tin nhắn | Gửi SMS |
| `send_appointment_confirmation(email, phone, details)` | Thông tin lịch hẹn | Gửi xác nhận lịch hẹn (email + SMS) |
| `send_intake_completion(email, phone, summary)` | Tóm tắt intake | Thông báo hoàn thành thu thập (email + SMS) |
| `send_reminder(phone, type, details)` | Loại nhắc nhở | Gửi SMS nhắc nhở |
| `get_notification_history(limit)` | Số lượng | Xem lịch sử gửi |

## Singleton
```python
from services import notification_service
```

## Tích hợp (chưa kết nối)
Gọi `notification_service.send_intake_completion()` sau khi sự kiện `intake_complete` được gửi về frontend.
