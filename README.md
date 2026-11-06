# Canada Scholarships

Thu thập và chuẩn hóa dữ liệu của 13 trường Canada. **Một trường = một file Python để chỉnh logic + một file JSON kết quả.**

```text
schools/
  humber_polytechnic.py          URL và quy tắc của Humber
  lakehead_university.py         URL và cách nối footnote của Lakehead
  ibu_university.py              URL và quy tắc xử lý nội dung IBU
  ...                           các trường còn lại
outputs/
  humber_polytechnic.json        dữ liệu chuẩn hóa, bằng chứng và trạng thái crawl
  lakehead_university.json
  ibu_university.json
  ...
pipeline.py                     xử lý HTTP, DOM, tiền/ngày/điểm và format dùng chung
run_all.py                      lệnh chạy duy nhất
schema/scholarships.sql          schema CSDL tham chiếu
bao_cao_nghien_cuu_scholarship_canada.md
```

## Chạy

```bash
python3 -m pip install -r requirements.txt
python3 run_all.py --list
python3 run_all.py --school humber
python3 run_all.py --school lakehead_university
python3 run_all.py
```

Có thể chạy trực tiếp file trường:

```bash
python3 schools/humber_polytechnic.py
```

Tùy chọn: `--workers 4`, `--timeout 12`, `--output-dir /tmp/scholarships`. Tên trường có thể là slug đầy đủ hoặc chuỗi khớp duy nhất. Exit code: 0 khi các trường được chọn đều thành công, 1 nếu có lỗi, 2 nếu tham số không hợp lệ.

Một lệnh lấy HTML và xuất thẳng JSON; không cần chạy script export sau đó. Chạy một trường chỉ cập nhật file của trường đó. Không có summary, thư mục final lồng nhau, generator hoặc dữ liệu trung gian được xuất riêng. File lỗi vẫn ghi trạng thái thất bại và không chứa học bổng giả.

## Sửa một trường

Mở `schools/<slug>.py`. Mỗi file chứa `name`, `slug`, `url` và các phương thức riêng nếu trường cần xử lý khác:

- `parse_html(soup)`: override khi DOM riêng cần cách trích xuất khác.
- `renewal_footnotes(data, value_text, file)`: nối bằng chứng footnote vào tier, như Lakehead.
- `keep_section(candidate)`: giữ nhóm nội dung phù hợp, như nhóm domestic của IBU.
- `candidate_issue(candidate)`: ghi nhận vùng chưa đủ bằng chứng để coi là award riêng.

Các hàm HTTP/chuẩn hóa phổ biến dùng lại trong `pipeline.py`; không sao chép toàn bộ bộ xử lý vào 13 file. Thêm trường mới bằng cách tạo một file tương tự có `class Crawler(SchoolCrawler)`; runner tự tìm module, không cần cập nhật registry ở nơi khác.

## Đọc JSON

Mỗi `outputs/<slug>.json` có `schema_version: 3` và các nhóm:

| Trường | Nội dung |
|---|---|
| `school`, `crawl`, `source` | Trường, trạng thái HTTP/các lần thử, URL và thời gian lấy nguồn. |
| `scholarships` | Mục award có tên và bằng chứng riêng, chưa được duyệt. |
| `scholarship_groups[].tiers` | Nhóm và các bậc điểm/giá trị/gia hạn. |
| `application_windows` | Lịch mở/đóng hồ sơ theo nhóm hoặc học kỳ. |
| `cost_breakdowns` | Học phí/chi phí/giảm trừ, tách riêng khỏi giá trị học bổng. |
| `unresolved_sections` | Phần chưa đủ điều kiện chuẩn hóa; kèm văn bản để đọc ngay. |
| `evidence.tables`, `evidence.renewal` | Bảng và điều kiện gốc, đủ để đối chiếu ngay trong cùng file. |
| `summary` | Số mục có tên, nhóm, tier và lịch hồ sơ của riêng trường. |

Mọi `json_pointer` trỏ vào chính file trường đó. Không cần file raw hoặc HTML khác để đọc bằng chứng. Hash HTML vẫn được giữ nếu có, nhưng HTML không được xuất thành file thứ hai.

Các mục vẫn có trạng thái `needs_review`, không tự công bố. Currency chỉ được gắn khi có bằng chứng rõ; chưa biết giữ null/unknown. Không dùng min/max tiền của cả trang làm giá trị award. Giá trị theo kỳ, năm và toàn khóa được giữ riêng; deadline thiếu năm không bị tự bổ sung năm. `total_scholarships = null` cho đến khi có bước xác nhận các gói độc lập.

## Dữ liệu đã chuyển sang cấu trúc mới

13 file hiện tại được chuyển từ dữ liệu crawl trước khi tinh gọn, giữ nguyên thời gian lấy nguồn và trạng thái 10 trường thành công / 3 trường bị chặn. `source.input_kind = legacy_json_import` phân biệt việc chuyển đổi với crawl mới; hash JSON đầu vào cũ được giữ để truy vết. Sau khi chạy lại một trường, file mới ghi `input_kind = live_http`.

Bản sao đầy đủ của repo trước khi dọn nằm **ngoài repo**, cùng thư mục cha, tên `Scholarship-backup-20261106-101222.tar.gz`. Báo cáo nghiên cứu được giữ như ghi nhận của đợt khảo sát trước; không tự viết lại khi crawl.

## Kiểm tra

```bash
python3 -m unittest discover -s tests -v
python3 tests/check_schema.py
```

Kiểm tra SQL dùng PostgreSQL 16 trong Docker tạm, không mở cổng host và tự xóa container sau khi chạy. Không có thao tác triển khai vào database LOA Portal.
