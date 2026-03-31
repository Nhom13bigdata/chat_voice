# 🔧 Utils — Validators & Audio Processing

## `validators.py` — Kiểm Tra Dữ Liệu

Tất cả trả về `Tuple[bool, Optional[str]]` — `(is_valid, error_or_formatted_value)`.

| Hàm | Chức năng | Ví dụ |
|-----|-----------|-------|
| `validate_phone_number(phone)` | Validate + format SĐT US | `"5551234567"` → `"(555) 123-4567"` |
| `validate_email(email)` | Kiểm tra format email | regex pattern |
| `validate_date_of_birth(dob)` | Kiểm tra ngày sinh hợp lệ | Hỗ trợ `YYYY-MM-DD`, `MM/DD/YYYY` |
| `validate_allergy_severity(severity)` | Kiểm tra mức độ dị ứng | `mild/moderate/serious/life-threatening` |
| `sanitize_text_input(text, max_length)` | Xóa ký tự điều khiển, giới hạn độ dài | Loại bỏ `\x00-\x1F` |
| `validate_medication_name(med)` | Kiểm tra tên thuốc | 2–100 ký tự, chỉ chữ/số |
| `validate_symptom_severity(severity)` | Kiểm tra mức nghiêm trọng 1–10 | Trích số từ text |
| `validate_insurance_member_id(id)` | Kiểm tra ID BHYT | 6–20 ký tự alphanumeric |
| `validate_medical_record_completeness(data)` | Kiểm tra đủ trường bắt buộc | `patient_info`, `present_illness`, `allergies` |
| `validate_critical_allergies(allergies)` | Validate danh sách dị ứng | Kiểm tra cấu trúc + severity |

---

## `audio_processing.py` — Xử Lý Audio

Class `AudioProcessor` — xử lý audio PCM cơ bản.

| Method | Chức năng |
|--------|-----------|
| `validate_audio_chunk(data)` | Kiểm tra kích thước chunk có đúng alignment |
| `get_audio_duration(data)` | Tính thời lượng audio (giây) |
| `detect_silence(data, threshold)` | Phát hiện im lặng (amplitude < threshold) |

```python
from utils import audio_processor  # singleton sẵn sàng dùng
```

> ⚠️ Cả validators và audio processor đều **chưa được tích hợp** vào luồng chính. Có thể dùng để validate `extracted_data` hoặc kiểm tra audio quality trước khi gửi lên Gemini.
