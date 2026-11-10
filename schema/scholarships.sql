-- Schema tra cứu học bổng theo trường (PostgreSQL).
-- Phạm vi mục tiêu: entrance có nhận international, kể cả transfer entrance.
-- Bước chọn dữ liệu phải kiểm tra phạm vi này; SQL không tự lọc từ requirements.
-- Một trường có nhiều học bổng. Ngành/khoa và ngoại lệ ghi trong requirements.
-- Chưa phải migration cho database đang chạy; crawler vẫn xuất JSON riêng.
BEGIN;

CREATE TABLE schools (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE
);

CREATE TABLE scholarships (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    school_id BIGINT NOT NULL REFERENCES schools(id),
    name TEXT NOT NULL,
    type TEXT,                       -- scholarship, bursary, award; NULL khi chưa rõ.
    value_text TEXT,                 -- Quyền lợi, tiền tệ, kỳ cấp và các mức theo điểm.
    requirements TEXT,               -- Toàn bộ điều kiện: đối tượng, ngành, kỳ, điểm, gia hạn...
    deadline TEXT,                   -- Giữ đúng ngày/kỳ từ nguồn; không tự thêm năm/giờ.
    source_url TEXT NOT NULL CHECK (length(trim(source_url)) > 0),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by TEXT                  -- ID người sửa hoặc tên script; NULL khi chưa biết.
);

CREATE INDEX idx_scholarships_school ON scholarships(school_id);
COMMIT;

-- Danh sách học bổng của trường đang xem; $1 là slug truyền từ ứng dụng.
-- SELECT s.* FROM scholarships s
-- JOIN schools sc ON sc.id = s.school_id
-- WHERE sc.slug = $1
-- ORDER BY s.name, s.id;
-- Chọn ngành không tự lọc kết quả: người xem đối chiếu requirements.

-- Khi sửa nội dung, ứng dụng/ingestion phải ghi updated_at = CURRENT_TIMESTAMP
-- và updated_by = định danh người/script thực sự thực hiện thay đổi.
-- DEFAULT chỉ đặt thời điểm khi INSERT, không tự chạy lại khi UPDATE.
-- Đây là lần sửa bản ghi gần nhất, không phải thời điểm cập nhật trang nguồn.
