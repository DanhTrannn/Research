# BÁO CÁO NGHIÊN CỨU DỮ LIỆU HỌC BỔNG CANADA VÀ THIẾT KẾ SCHEMA CHO LOA PORTAL

## 1. Mục tiêu và phạm vi

Mục tiêu là xác định cấu trúc dữ liệu cần thiết để lưu trữ, tra cứu và hiển thị học bổng đúng trường, đúng đối tượng, đúng kỳ tuyển sinh và đúng giá trị tài chính.

Phạm vi mục tiêu là học bổng **entrance có nhận sinh viên quốc tế**, kể cả transfer entrance khi nguồn cho phép. Đây là điều kiện chọn dữ liệu ở bước crawl/chuẩn hóa, không phải thuộc tính tự động có trong mọi output.

Bốn nhóm được chấp nhận: **Entrance Scholarship**, **International Student Scholarship**, **Admission Award** và **Academic Excellence Scholarship**. Bursary, domestic-only, continuing và non-entrance bị loại.

Nghiên cứu trả lời bốn câu hỏi:

1. Mỗi trường công bố học bổng theo dạng nào: trang tổng quan, section, bảng điểm hay danh mục award?
2. Có thể thu thập dữ kiện nào và truy lại nguồn ở đâu?
3. Một gói học bổng được phân biệt với trường, bậc điểm và kỳ tuyển sinh như thế nào?
4. Cần schema nào để không nhập nhầm dữ liệu khi chuyển từ HTML sang CSDL?

Đây là bộ dữ liệu nghiên cứu và crawler, chưa phải danh mục học bổng đã được duyệt để công bố.

## 2. Nguồn và phương pháp

Nguồn là các URL chính thức thuộc website của từng trường.

Quy trình hiện hành:

1. **Lấy trang:** thử `requests`, sau đó `curl`; nếu bị chặn hoặc cần JavaScript thì chuyển Selenium.
2. **Kiểm tra nội dung:** phân biệt HTTP 200 hợp lệ với challenge/WAF, trang lỗi, nội dung không phải học bổng.
3. **Bóc tách có chọn lọc:** mỗi trường tự chọn đúng bảng, section, accordion hoặc tab panel của mình; không quét toàn bộ số tiền trên trang.
4. **Chuẩn hóa:** xuất JSON gọn theo schema v4, giữ trạng thái lấy trang và ghi chú cần kiểm tra.
5. **Không dùng fallback giả:** khi bị chặn hoặc lỗi, file vẫn được ghi với trạng thái tương ứng và `scholarships: []`.

Phương pháp ban đầu có lưu bản chụp HTML/hash để đối chiếu; pipeline hiện tại đã tinh gọn, không xuất raw DOM, hash hay candidate.

## 3. Kết quả hiện tại

| Chỉ tiêu | Kết quả |
|---|---:|
| Số trường trong code | 17 |
| Trường lấy được dữ liệu (`ok`) | 16 |
| Trường bị chặn | 1 |
| Tỷ lệ trường `ok` | 94,1% |
| Tổng bản ghi trong `outputs/` | 57 |
| Bản ghi mang cờ `expired` | 4 |
| Học bổng đã được xác minh | 0 |

Trường bị chặn hiện tại là **Nipissing University** (HTTP 403). Brock và Alberta lấy được dữ liệu bằng Selenium; các trường còn lại dùng requests. Tất cả output thành công đều có `data_status = needs_review`.

Toàn bộ 57 bản ghi đã qua kiểm tra `scope_ok`: 0 record domestic, bursary, continuing hoặc non-entrance. Bốn record của IBU được giữ nhưng mang `expired: true` vì nguồn ghi hết hiệu lực cuối 2025; cần lọc theo cờ này khi hiển thị.

## 4. Phát hiện chính và yêu cầu thiết kế

| Phát hiện | Yêu cầu thiết kế |
|---|---|
| **Một trường có nhiều gói học bổng.** uOttawa có International English Admission Scholarship và Academic Excellence Scholarship với điều kiện, giá trị và gia hạn khác nhau. | Một trường liên kết với nhiều `scholarships`. Không tạo một bản ghi đại diện cho toàn trường. |
| **Một gói có nhiều bậc điểm và quy tắc gia hạn.** Lakehead có ba bậc 90%+, 80–89,9% và 75–79,9%; mức tiền và điều kiện gia hạn khác nhau. Humber cũng có nhiều bậc. | Giữ điểm, giá trị và điều kiện gia hạn theo từng tier. Không gán một cờ renewable hoặc một dải tiền chung cho mọi bậc. |
| **Số tiền trên trang chưa chắc là học bổng.** IBU có học phí trước/sau khấu trừ và tiền đặt cọc; Lethbridge có `$800` đứng sát dải điểm `75–79.9%`. | Chỉ ghi giá trị sau khi xác định đúng quyền lợi, tiền tệ và kỳ cấp. Giữ `value_text` và link nguồn để đối chiếu. |
| **Đối tượng và phạm vi ngành là dữ liệu nghiệp vụ.** Algonquin có cột `Open to International?`, `Term`, `Application Required?`; MacEwan tách domestic và international, crawler chỉ xuất series international. | Ghi đối tượng, bậc học, ngành/khoa, kỳ và điều kiện vào `requirements`. Ô trống là chưa xác định, không tự chuyển thành `false`. |
| **Kỳ tuyển sinh, deadline và lịch chi trả phải tách riêng.** Lakehead có intake; uOttawa có tiền theo kỳ, tổng toàn khóa và số lần trả tối đa; Regina có lịch hồ sơ; Queen’s có ngày chi trả. | Giữ kỳ áp dụng trong `requirements`, hạn nộp trong `deadline`. Không coi ngày chi trả là deadline và không tự nhân số kỳ khi nguồn chưa rõ. |
| **Mỗi gói cần link nguồn chính thức.** Nội dung có thể bị chặn, thiếu điều kiện hoặc thay đổi theo thời gian. | Mỗi scholarship giữ `source_url`; người xem mở nguồn để đọc điều khoản và cách nộp. |

## 5. Schema tinh gọn

Giả định bảng `schools` đã có trong LOA Portal. Báo cáo chỉ mô tả bảng `scholarships`; mỗi scholarship liên kết với trường qua `school_id`. Không tách bảng ngành, bảng nối ngành hay bảng tier.

### 5.1. Bảng `scholarships`

| Field | Ý nghĩa |
|---|---|
| `id` | ID nội bộ |
| `school_id` | Liên kết tới bảng `schools` hiện có; xác định trường sở hữu học bổng |
| `name` | Tên học bổng |
| `type` | Scholarship, bursary hoặc award; NULL khi chưa rõ |
| `value_text` | Quyền lợi, tiền tệ, kỳ cấp và các mức theo điểm |
| `requirements` | Đối tượng, quốc tịch, bậc học, ngành, kỳ, điểm, ngoại ngữ, chuyển tiếp, học toàn thời gian, gia hạn |
| `deadline` | Hạn nộp theo nguồn; NULL nếu chưa rõ |
| `source_url` | Trang chính thức để đọc điều khoản và cách nộp |
| `updated_at` | Thời điểm tạo/cập nhật bản ghi gần nhất |
| `updated_by` | ID người hoặc tên script cập nhật; NULL nếu chưa biết |

DDL tham khảo:

```sql
BEGIN;

CREATE TABLE scholarships (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    school_id BIGINT NOT NULL REFERENCES schools(id),
    name TEXT NOT NULL,
    type TEXT,                       -- scholarship, bursary, award; NULL khi chưa rõ
    value_text TEXT,                 -- quyền lợi, tiền tệ, kỳ cấp, mức theo điểm
    requirements TEXT,               -- đối tượng, ngành, kỳ, điểm, gia hạn...
    deadline TEXT,                   -- giữ đúng ngày/kỳ từ nguồn
    source_url TEXT NOT NULL CHECK (length(trim(source_url)) > 0),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by TEXT
);

CREATE INDEX idx_scholarships_school ON scholarships(school_id);
COMMIT;
```

`schools` là bảng có sẵn; `scholarships.school_id` chỉ là khóa ngoại. Output hiện tại đã loại bursary, nhưng schema vẫn cho phép `type = 'bursary'` nếu sau này cần lưu ngoài phạm vi.

### 5.2. Ánh xạ JSON crawler → database

| JSON | Database |
|---|---|
| `school.name`, `school.slug` | Tra cứu trường trong bảng `schools` hiện có để lấy `school_id` |
| `name`, `type` | `scholarships.name`, `scholarships.type` |
| `value_text`, `value_texts`, `values`, `tiers`, `benefits` | `scholarships.value_text` |
| `eligibility`, `applicant_category`, `eligible_stages`, `programs`, `intakes`, `renewable`, `renewal_conditions` | `scholarships.requirements` |
| Deadline của gói | `scholarships.deadline` |
| `source_url` | `scholarships.source_url` |
| Thao tác ghi/cập nhật | `updated_at`, `updated_by` |

### 5.3. Quy tắc tracking

- Khi tạo bản ghi: `updated_at` dùng `CURRENT_TIMESTAMP`; bên ghi cung cấp `updated_by` nếu xác định được.
- Khi sửa nội dung: cập nhật đồng thời `updated_at` và `updated_by`.
- `DEFAULT` không tự chạy lại khi `UPDATE`.
- Hai field chỉ ghi lần sửa bản ghi gần nhất, không phải thời điểm website nguồn thay đổi và không lưu toàn bộ lịch sử.
- Không dùng `fetched_at` của JSON làm `updated_at`.

### 5.4. Phạm vi dữ liệu

SQL không tự lọc học bổng theo ngành hoặc theo phạm vi international entrance. Bước chọn dữ liệu trước khi nhập database phải kiểm tra:

- Có thuộc một trong bốn nhóm: Entrance Scholarship, International Student Scholarship, Admission Award, Academic Excellence Scholarship?
- Có dành cho sinh viên quốc tế không (`applicant_category`; nhóm open-to-all cần `international_eligible=True`)?
- Có phải entrance hoặc transfer entrance không (`eligible_stages`)?
- Có phải bursary, domestic-only, continuing hoặc non-entrance không? Nếu có, loại.
- Record đó là một gói cụ thể hay chỉ là heading/nhóm danh mục?

## 6. Giới hạn và hướng hoàn thiện

- Kết quả hiện tại không đại diện cho toàn bộ học bổng của 17 trường; một số nguồn bị chặn hoặc chỉ đọc trang tổng quan.
- Output đã được lọc đồng bộ theo phạm vi international entrance; kiểm tra `scope_ok` cho 57/57 record đạt, 0 record ngoài phạm vi.
- Bốn record IBU mang cờ `expired: true`; Lethbridge vẫn là nhóm award rộng, không phải từng award riêng.
- Một số điều kiện nằm trong footnote, trang liên kết hoặc tab khác chưa được thu thập đầy đủ.
- Schema ưu tiên đọc và tra cứu, chưa hỗ trợ tự động tính mức học bổng hoặc khẳng định ứng viên đủ điều kiện.
- Chưa có ETL nhập JSON vào database và chưa triển khai schema vào LOA Portal.
- Chưa có test tự động; extractor gắn với cấu trúc HTML hiện tại nên cần kiểm tra lại khi website đổi.
- Hướng tiếp theo: bổ sung ETL, test/regression, xử lý rate limit/robots và xác minh thủ công các record `needs_review`.

## 7. Hiện trạng và kết luận

Code hiện tại có **17 trường**. Lần chạy gần nhất có **16 trường `ok`**, **1 trường bị chặn** là Nipissing (HTTP 403), **57 bản ghi** và **0 học bổng đã xác minh**. Brock và Alberta lấy được dữ liệu bằng Selenium. Tất cả output thành công đều có `data_status = needs_review`, nghĩa là cần kiểm tra trước khi dùng chính thức. Trong 57 bản ghi, 4 record IBU mang cờ `expired: true`.

Các kết luận chính vẫn giữ nguyên:

1. Mỗi trường có nhiều gói học bổng; mỗi gói có thể có nhiều tier và điều kiện riêng.
2. Không được lấy mọi con số trên trang làm giá trị học bổng.
3. Phải tách quyền lợi, điều kiện, kỳ tuyển sinh, deadline và lịch chi trả.
4. Phải giữ link nguồn chính thức để đối chiếu.
5. Bảng `scholarships` liên kết với `schools` là đủ cho mục tiêu tra cứu hiện tại; chưa cần mô hình quan hệ phức tạp hơn.

Đây là thiết kế tham khảo cho LOA Portal, chưa phải migration database đang chạy và chưa có bước tự động nhập dữ liệu.
