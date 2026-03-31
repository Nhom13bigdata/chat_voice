# 🏦 Insurance Service (`insurance_service.py`)

## Mục đích
Xác minh bảo hiểm y tế và kiểm tra quyền lợi bệnh nhân.

## Status: 🟡 Mock
Trả dữ liệu mẫu — cần tích hợp API bảo hiểm thực khi deploy.

## API

| Method | Tham số | Chức năng |
|--------|---------|-----------|
| `verify_coverage(member_id, provider)` | ID thành viên + nhà cung cấp | Xác minh bảo hiểm còn hiệu lực |
| `check_eligibility(member_id, provider, service_type)` | + loại dịch vụ | Kiểm tra đủ điều kiện cho dịch vụ |
| `get_benefits(member_id, provider)` | ID + nhà cung cấp | Xem quyền lợi chi tiết |
| `submit_pre_authorization(member_id, provider, procedure, diagnosis)` | Mã thủ thuật + chẩn đoán | Gửi yêu cầu phê duyệt trước |

## Singleton
```python
from services import insurance_service
```

## Tích hợp (chưa kết nối)
Có thể gọi khi bệnh nhân cung cấp thông tin bảo hiểm trong cuộc hội thoại.
