# 📋 EMR Service (`emr_service.py`)

## Mục đích
Quản lý hồ sơ bệnh án điện tử (Electronic Medical Records).

## Status: 🟡 Mock
Đang dùng **in-memory dict** — cần thay bằng database/API thực khi deploy.

## API

| Method | Tham số | Chức năng |
|--------|---------|-----------|
| `save_intake(intake_data)` | Dict dữ liệu y tế | Lưu kết quả intake → trả `record_id` |
| `get_patient_history(patient_id)` | ID bệnh nhân | Truy vấn tiền sử bệnh |
| `update_patient_record(record_id, updates)` | ID record + dict cập nhật | Cập nhật hồ sơ |
| `search_patient(name, dob, phone)` | Các tiêu chí tìm kiếm | Tìm bệnh nhân |

## Singleton
```python
from services import emr_service  # instance sẵn sàng dùng
```

## Tích hợp (chưa kết nối)
Có thể gọi `emr_service.save_intake()` trong `_send_to_frontend()` khi nhận sự kiện `complete_intake`, sau khi trích xuất `structured_data`.
