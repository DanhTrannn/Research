# Canada Scholarships

Crawler dữ liệu học bổng entrance dành cho sinh viên quốc tế tại các trường Canada. Mỗi trường là một file Python; kết quả là một JSON gọn trong `outputs/`.

## Phạm vi

Output chỉ giữ bốn nhóm:

- **Entrance Scholarship** — dành cho sinh viên mới nhập học.
- **International Student Scholarship** — dành cho sinh viên quốc tế.
- **Admission Award** — giải thưởng khi xét tuyển đầu vào.
- **Academic Excellence Scholarship** — dựa trên GPA/thành tích học tập.

Transfer entrance được giữ khi nguồn ghi rõ. Bursary thuần túy, domestic-only, continuing và non-entrance bị loại. `pipeline.scope_ok` kiểm tra `applicant_category`, `international_eligible` (bắt buộc với nhóm open-to-all) và `eligible_stages`.

## Chạy

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

python run_all.py
python run_all.py --school humber
python run_all.py --list
```

Tùy chọn: `--workers 4`, `--timeout 12`, `--output-dir /tmp/scholarships`, `--browser auto|selenium|http`, `--headed`, `--headless`. Chạy một trường chỉ cập nhật file của trường đó.

## Kết quả hiện tại

| Chỉ tiêu | Kết quả |
|---|---:|
| Số trường | 17 |
| Trường `ok` | 16 |
| Trường bị chặn | 1 — Nipissing University (HTTP 403) |
| Tổng bản ghi | 57 |
| Bản ghi ngoài phạm vi | 0 |
| Bản ghi `expired` | 4 — IBU |
| Học bổng đã xác minh | 0 |

Tất cả output thành công có `data_status = needs_review`. Bốn award quốc tế của IBU được giữ vì quyền lợi công bố là International/Regional Scholarship, nhưng nguồn ghi hết hiệu lực cuối 2025 nên mang `expired: true`.

## Output

```json
{
  "schema_version": 4,
  "school": {"name": "Tên trường", "slug": "ten_truong"},
  "source_url": "https://example.org/scholarships",
  "status": "ok",
  "http_status": 200,
  "transport": "requests",
  "data_status": "needs_review",
  "scholarships": [
    {
      "name": "Tên học bổng",
      "type": "scholarship",
      "applicant_category": "international",
      "international_eligible": true,
      "eligible_stages": ["entrance"],
      "value_text": "$10,000",
      "values": [{"min_amount": 10000, "max_amount": 10000, "payment_basis": "per_year"}]
    }
  ]
}
```

Thiếu field nghĩa là chưa xác định, không phải `false`. Khi bị chặn hoặc lỗi, file vẫn được ghi với status tương ứng và `scholarships: []`.

## Cấu trúc project

```text
pipeline.py     HTTP, parse, chuẩn hóa, ghi JSON
run_all.py      chạy một hoặc tất cả trường
schools/        mỗi trường một crawler
outputs/        kết quả JSON
report.md       phạm vi, thiết kế schema và kết quả chi tiết
```

## Selenium

Mặc định `--browser auto`: thử requests/curl trước, chuyển Selenium khi bị chặn hoặc cần JavaScript.

```bash
python run_all.py --school brock --browser selenium --headed
python run_all.py --school alberta --browser selenium --headed
python run_all.py --school nipissing --browser selenium --headed --browser-wait 90
```

Với Nipissing, dùng profile riêng nếu cần xác minh thủ công:

```bash
python run_all.py --school nipissing --browser selenium --headed \
  --browser-profile .browser-profiles/nipissing --manual-challenge-wait 180
```

`.browser-profiles/` đã được gitignore. Script không tự giải CAPTCHA; nếu challenge không qua được, status vẫn là `blocked`.

## Tài liệu

Chi tiết phạm vi, schema `scholarships` và kết quả từng trường: [report.md](report.md).
