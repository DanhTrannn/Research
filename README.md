# Canada Scholarships

**Một trường = một file Python xử lý đầy đủ + một file JSON kết quả gọn.**

```text
schools/humber_polytechnic.py     crawl() → extract() → export()
outputs/humber_polytechnic.json   kết quả cần sử dụng của Humber
pipeline.py                      tiện ích HTTP, đọc bảng/section, tiền/ngày và ghi JSON
run_all.py                       chạy một hoặc tất cả trường
```

## Chạy

```bash
python3 -m pip install -r requirements.txt
python3 schools/humber_polytechnic.py
python3 run_all.py --school lakehead
python3 run_all.py
python3 run_all.py --list
```

Tùy chọn: `--workers 4`, `--timeout 12`, `--output-dir /tmp/scholarships`. Tên trường có thể là slug hoặc chuỗi khớp duy nhất. Chạy một trường chỉ cập nhật file trường đó. Không cần script export riêng.

## Sửa logic của một trường

Mở `schools/<slug>.py`. Mỗi file có ba bước rõ ràng:

1. `crawl(timeout)`: lấy HTML từ URL của trường, kiểm tra HTTP và challenge.
2. `extract(soup)`: chọn đúng bảng/section của trường, trích xuất thông tin học bổng cần dùng.
3. `export(metadata, data, output_dir)`: ghi JSON đã lọc.

`run()` nối ba bước này trong chính file trường. Bộ xử lý chung không chọn thay trường toàn bộ nội dung trang. Ví dụ:

- Humber chọn bảng `Average/Amount`, hai nhóm bursary có tên và lịch hồ sơ; bỏ FAQ/bảng chi phí.
- Lakehead chọn bảng đầu vào, nối footnote đúng số với tier và giữ giá trị theo năm/toàn khóa riêng.
- IBU đọc panel đúng `aria-controls` của từng tab; chỉ lấy các dòng giảm trừ Scholarship, không lấy học phí hoặc deposit làm quyền lợi.
- Algonquin giữ tên award, tiêu chí, campus, đối tượng quốc tế, học kỳ và cách nộp; không xuất lại toàn bộ DOM.
- Regina lấy lịch hồ sơ vì URL là trang tổng quan, không dựng một gói tiền chung cho cả trường.

Thêm trường bằng một file có `class Crawler` và các phương thức tương tự. Runner tự nhận diện file, không có generator hoặc registry riêng.

## JSON gọn — phiên bản 4

```json
{
  "schema_version": 4,
  "school": {"name": "Tên trường", "slug": "ten_truong"},
  "source_url": "https://example.org/scholarships",
  "fetched_at": "thời điểm crawl",
  "status": "ok",
  "http_status": 200,
  "data_status": "needs_review",
  "scholarships": [
    {
      "name": "Tên học bổng",
      "tiers": [
        {
          "grade_text": "95%+",
          "value_text": "$4,000 renewable",
          "values": [{"min_amount": 4000, "max_amount": 4000, "payment_basis": "unknown"}],
          "renewable": true
        }
      ]
    }
  ]
}
```

Đây là ví dụ hình dạng dữ liệu, không phải một học bổng đã xác minh. Các trường không có thông tin được bỏ thay vì xuất nhiều null/mảng rỗng. `false` và số 0 vẫn được giữ. Thiếu trường có nghĩa chưa xác định, không phải false hoặc không áp dụng.

Dữ liệu chỉ gồm phần đã chọn: tên, loại/đối tượng, ngành, điều kiện, mức tiền, bậc điểm, gia hạn, kỳ/hạn nộp và nguồn. Một số trang có thêm `application_periods` hoặc `notes` khi cần diễn giải. Không còn hash, ID kỹ thuật, JSON pointer, bảng/cell/grid thô, danh sách candidate, raw evidence, source_tables hoặc thống kê lặp trong output. Các câu điều kiện cần thiết vẫn giữ nguyên nghĩa để không mất các ngoại lệ quan trọng.

Currency chỉ được gắn khi có bằng chứng rõ. Các giá trị theo kỳ, năm và toàn khóa giữ riêng, không tự cộng. Deadline không nêu năm thì giữ ngày/tháng gốc. Không gán `renewable: true` cho mọi tier chỉ vì một phần của trang đề cập gia hạn. IBU giữ thông tin hiệu lực/expired theo nội dung tab, không coi grant cũ là còn áp dụng.

`data_status = needs_review` áp dụng cho toàn bộ kết quả: schema gọn không đồng nghĩa mọi điều khoản đã được xác minh. Khi bị chặn hoặc lỗi, file vẫn được ghi với status tương ứng và `scholarships: []`. Không có fallback dữ liệu giả. Exit code 0 khi tất cả trường được chọn có dữ liệu; 1 nếu có trường lỗi/không trích xuất được; 2 nếu tham số không hợp lệ.

## Tài liệu và bản cũ

Giữ [báo cáo nghiên cứu](bao_cao_nghien_cuu_scholarship_canada.md) và [schema PostgreSQL](schema/scholarships.sql) để tham khảo. Báo cáo mô tả đợt nghiên cứu trước, không tự viết lại sau mỗi lần crawl. Output schema v4 thay thế schema v3 nên code đọc JSON cần dùng cấu trúc mới.

Phiên bản output/script trước có thể đối chiếu trong lịch sử Git. Không có thư mục tests hoặc công cụ export trung gian được thêm lại.
