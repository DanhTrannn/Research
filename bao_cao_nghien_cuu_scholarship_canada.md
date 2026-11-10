# BÁO CÁO NGHIÊN CỨU DỮ LIỆU HỌC BỔNG CANADA VÀ THIẾT KẾ SCHEMA CHO LOA PORTAL

> **Cách đọc báo cáo:** phần 2–3 ghi nhận đợt khảo sát ban đầu của 13 trường; số liệu và mô tả output ở đó không phải trạng thái hiện tại. Phần 4–6 đã cập nhật theo thiết kế hiện hành: hai bảng `schools`/`scholarships`, điều kiện trong `requirements`, link `source_url`, tracking bằng `updated_at`/`updated_by`. Mã hiện tại dùng `run_all.py`, `pipeline.py`, mỗi trường một script trong `schools/` và một JSON gọn trong `outputs/`. Dữ liệu mới xem ở các file JSON; phiên bản mã/tài liệu cũ đối chiếu trong Git. Database vẫn là thiết kế tham khảo, chưa có script nhập dữ liệu tự động.


## 1. Mục tiêu và phạm vi nghiên cứu

Mục tiêu là xác định cấu trúc dữ liệu cần thiết để LOA Portal lưu trữ, tra cứu và hiển thị học bổng đúng trường, đúng đối tượng, đúng kỳ tuyển sinh và đúng giá trị tài chính.

Nghiên cứu tập trung trả lời các câu hỏi:

1. Website của mỗi trường công bố dữ liệu học bổng theo dạng nào: trang tổng quan, phần nội dung theo gói, bảng bậc điểm hay danh mục nhiều award?
2. Có thể thu thập được những dữ kiện nào và truy lại bằng chứng ở đâu?
3. Một gói học bổng cần được phân biệt với trường, bậc học bổng và phiên bản theo intake như thế nào?
4. Cần thiết kế các thực thể, quan hệ và ràng buộc nào để không nhập nhầm dữ liệu khi chuyển từ HTML sang CSDL?

Đầu ra của nghiên cứu gồm bộ bằng chứng HTML/JSON, các mục cần duyệt được parser tách ra, và schema PostgreSQL tham chiếu. Đây chưa phải danh mục học bổng đã được duyệt để công bố; nghiên cứu cũng không khẳng định đã thu thập hết mọi học bổng của 13 trường.

## 2. Nguồn tham khảo và cách thu thập

### 2.1. Danh mục nguồn chính thức

Mỗi nguồn là một URL thuộc website trường. Đây là URL mục tiêu của crawler; việc một URL xuất hiện trong danh mục không đồng nghĩa đã tải thành công. Trạng thái lấy trang và file kết quả được trình bày riêng ở mục 3.

| Mã nguồn | Trường | Trang tham khảo chính thức |
|---|---|---|
| S01 | Algonquin College | [Trang chính thức](https://www.algonquincollege.com/financial-aid/awards-bursaries-scholarships/) |
| S02 | Brock University | [Trang chính thức](https://brocku.ca/safa/2026-international-students/) |
| S03 | Humber Polytechnic | [Trang chính thức](https://humber.ca/study-at-humber/pay-fees/scholarships-bursaries) |
| S04 | International Business University (IBU) | [Trang chính thức](https://ibu.ca/admission/undergraduate-admissions/undergraduate-tuition-fees/entrance-scholarships/) |
| S05 | Lakehead University | [Trang chính thức](https://www.lakeheadu.ca/international/future/scholarships-awards) |
| S06 | MacEwan University | [Trang chính thức](https://www.macewan.ca/apply-enrol/fees-finances/scholarships-awards-bursaries/entrance-scholarships/) |
| S07 | Nipissing University | [Trang chính thức](https://www.nipissingu.ca/studentsupports/student-financial-services/student-awards-and-financial-aid/guaranteed-entrance-scholarships) |
| S08 | Queen's University | [Trang chính thức](https://www.queensu.ca/registrar/financial-aid) |
| S09 | University of Alberta | [Trang chính thức](https://www.ualberta.ca/en/admissions/tuition-and-scholarships/international-entrance-scholarships/index.html) |
| S10 | University of Lethbridge | [Trang chính thức](https://www.ulethbridge.ca/ross/student-finance/awards) |
| S11 | University of Ottawa | [Trang chính thức](https://www.uottawa.ca/study/fees-financial-support/international-english-scholarship) |
| S12 | University of Regina | [Trang chính thức](https://www.uregina.ca/cost-aid/funding/undergraduate-scholarships/index.html) |
| S13 | University of Waterloo | [Trang chính thức](https://uwaterloo.ca/future-students/financing/scholarships) |

Các trang tổng quan như Regina, Queen’s và Lethbridge còn dẫn sang danh mục/điều khoản chi tiết. Crawler hiện thu thập các URL đã cấu hình, chưa tự duyệt hết mọi liên kết con. Điều khoản ở một trang khác chưa được thu thập thì vẫn là phần thiếu bằng chứng.

### 2.2. Phương pháp nghiên cứu ban đầu

Quy trình dưới đây mô tả đợt nghiên cứu ban đầu. Pipeline hiện tại đã tinh gọn, không còn xuất bản chụp HTML/hash, bảng thô hay candidate; xem README để chạy crawler hiện hành.

Quy trình nghiên cứu ban đầu thực hiện theo thứ tự:

1. **Lấy trang:** dùng requests, sau đó curl nếu cần; theo chuyển hướng và lưu HTTP thực tế của từng lần thử.
2. **Kiểm tra nội dung:** phân biệt HTML học bổng với trang challenge, trang lỗi và phản hồi không phù hợp.
3. **Lưu bản chụp có nguồn:** ghi HTML kèm URL yêu cầu, URL đích, thời gian UTC và SHA-256. Đây là bằng chứng phản hồi đã nhận, không phải chứng nhận độc lập cho mọi phát biểu của website.
4. **Bóc tách DOM:** lấy heading, toàn bộ bảng/cell và span; giữ câu ngữ cảnh của số tiền, điều kiện, gia hạn và deadline.
5. **Tách mục cần duyệt:** tạo candidate theo heading, hàng có tên award hoặc hàng bậc điểm; giữ liên kết với vùng dữ liệu gốc.
6. **Phân tích nghiệp vụ:** đối chiếu các trường hợp thực tế để xác định đơn vị bản ghi, quan hệ, kiểu dữ liệu và quy tắc kiểm tra trước khi nhập CSDL.

Phương pháp này kết hợp trích xuất tự động với đọc và diễn giải dữ liệu đã lưu. Công cụ tự động bảo toàn bằng chứng; kết luận về giá trị học bổng phải dựa trên vùng nội dung, đối tượng và kỳ áp dụng tương ứng.

### 2.3. Quy ước đọc kết quả

| Khái niệm | Ý nghĩa trong báo cáo |
|---|---|
| Trang crawl thành công | Nhận HTML hợp lệ và parse được; chưa chứng minh mọi thông tin nghiệp vụ đã được xác minh. |
| Candidate | Một đơn vị cần duyệt: tên award, hàng tier hoặc nhóm nội dung. Có thể chồng lặp giữa heading và bảng. |
| Học bổng đã duyệt | Bản ghi đã xác định đúng tên gói, intake, đối tượng, giá trị và bằng chứng; không được đếm từ số trang/candidate. |
| `null` / `unknown` | Chưa đủ bằng chứng để kết luận; khác với `false`, số 0 hoặc áp dụng toàn trường. |
| HTTP 202/403 | Phản hồi có thể là WAF/challenge; không được coi là HTML học bổng hợp lệ. |

Crawler hiện tại không dùng fixture hay snapshot làm fallback và không còn tùy chọn `--allow-snapshot`. Các thuật ngữ snapshot/hash/candidate trong kết quả khảo sát dưới đây mô tả phiên bản nghiên cứu cũ; có thể đối chiếu phiên bản mã qua Git.

## 3. Kết quả nghiên cứu

### 3.1. Tổng hợp kết quả

| Chỉ tiêu | Kết quả |
|---|---:|
| Số trường yêu cầu | 13 |
| Số trường đã thử crawl | 13 |
| Số trường lấy được HTML hợp lệ | 10 |
| Số trường thất bại | 3 |
| Số trường dùng snapshot trong đợt này | 0 |
| Tổng số bảng HTML đã bóc tách | 27 |
| Tổng số hàng dữ liệu bảng đã lưu | 695 |
| Tổng số candidate cần duyệt | 695 |
| Số học bổng đã được duyệt bởi pipeline | 0 |
| Tổng số học bổng thực tế | Chưa xác định (`total_scholarships = null`) |

Tỷ lệ thu thập thành công là 76,92%. Toàn bộ 3 trường thất bại trong bộ dữ liệu này bị chặn bởi cơ chế bảo vệ truy cập. Tổng hàng bảng gồm cả bảng danh mục, quốc gia, chi phí và một số hàng tiêu đề mã hóa bằng `td`; số liệu này đo khối lượng cấu trúc HTML được giữ lại, không đo số học bổng. Bản dữ liệu tổng hợp được lưu để đối chiếu tại all_scholarships_summary.json (tài liệu lịch sử trong bản sao lưu).

### 3.2. Tổng quan kết quả khảo sát từng trường

Số liệu trong bảng thuộc đợt ban đầu; các link JSON trỏ tới output hiện hành và có thể khác số liệu lịch sử. Các mục HTML/metadata lịch sử không phải file được xuất bởi crawler hiện tại.

| Trường | Trạng thái / HTTP | Bảng | Hàng dữ liệu | Candidate | File kết quả | Bằng chứng HTML |
|---|---|---:|---:|---:|---|---|
| Algonquin College | Thành công / 200 | 1 | 590 | 591 | [JSON](outputs/algonquin_college.json) | HTML (tài liệu lịch sử trong bản sao lưu) · Metadata (tài liệu lịch sử trong bản sao lưu) |
| Brock University | Thất bại: blocked / 403 | 0 | 0 | 0 | [JSON](outputs/brock_university.json) | — |
| Humber Polytechnic | Thành công / 200 | 4 | 14 | 23 | [JSON](outputs/humber_polytechnic.json) | HTML (tài liệu lịch sử trong bản sao lưu) · Metadata (tài liệu lịch sử trong bản sao lưu) |
| International Business University (IBU) | Thành công / 200 | 7 | 37 | 7 | [JSON](outputs/ibu_university.json) | HTML (tài liệu lịch sử trong bản sao lưu) · Metadata (tài liệu lịch sử trong bản sao lưu) |
| Lakehead University | Thành công / 200 | 1 | 3 | 6 | [JSON](outputs/lakehead_university.json) | HTML (tài liệu lịch sử trong bản sao lưu) · Metadata (tài liệu lịch sử trong bản sao lưu) |
| MacEwan University | Thành công / 200 | 0 | 0 | 3 | [JSON](outputs/macewan_university.json) | HTML (tài liệu lịch sử trong bản sao lưu) · Metadata (tài liệu lịch sử trong bản sao lưu) |
| Nipissing University | Thất bại: blocked / 403 | 0 | 0 | 0 | [JSON](outputs/nipissing_university.json) | — |
| Queen's University | Thành công / 200 | 0 | 0 | 5 | [JSON](outputs/queens_university.json) | HTML (tài liệu lịch sử trong bản sao lưu) · Metadata (tài liệu lịch sử trong bản sao lưu) |
| University of Alberta | Thất bại: blocked / 202 | 0 | 0 | 0 | [JSON](outputs/university_of_alberta.json) | — |
| University of Lethbridge | Thành công / 200 | 1 | 6 | 8 | [JSON](outputs/university_of_lethbridge.json) | HTML (tài liệu lịch sử trong bản sao lưu) · Metadata (tài liệu lịch sử trong bản sao lưu) |
| University of Ottawa | Thành công / 200 | 0 | 0 | 6 | [JSON](outputs/university_of_ottawa.json) | HTML (tài liệu lịch sử trong bản sao lưu) · Metadata (tài liệu lịch sử trong bản sao lưu) |
| University of Regina | Thành công / 200 | 4 | 11 | 11 | [JSON](outputs/university_of_regina.json) | HTML (tài liệu lịch sử trong bản sao lưu) · Metadata (tài liệu lịch sử trong bản sao lưu) |
| University of Waterloo | Thành công / 200 | 9 | 34 | 35 | [JSON](outputs/university_of_waterloo.json) | HTML (tài liệu lịch sử trong bản sao lưu) · Metadata (tài liệu lịch sử trong bản sao lưu) |

**Cách sử dụng link:** JSON của trường thành công chứa dữ liệu trích xuất; HTML và metadata cho phép đối chiếu nguồn. JSON của trường thất bại chỉ ghi nguyên nhân và các lần thử, không chứa dữ liệu học bổng đã lấy được. Dấu `—` ở cột HTML nghĩa là không có bản chụp được sử dụng cho kết quả đó.

### 3.3. Kết quả nghiên cứu theo từng trường

Các nội dung dưới đây là kết quả đọc và diễn giải bộ HTML/JSON đã thu thập tại thời điểm nghiên cứu. Những thông tin định lượng chỉ được ghi nhận trong phạm vi gói, bậc và nhóm đối tượng nêu kèm; không suy rộng thành chính sách chung của cả trường.

#### 3.3.1. Algonquin College

Trang nghiên cứu tổ chức thông tin thành một danh mục có **590 hàng được parser lưu**, gồm các cột tên award, mô tả, loại quỹ, campus, khả năng áp dụng cho sinh viên quốc tế, học kỳ, yêu cầu hồ sơ riêng và cách nộp. Đây là cấu trúc giàu dữ liệu về đối tượng và phạm vi, nhưng không phải hàng nào cũng có số tiền.

Ba trường hợp được chọn để phân tích cấu trúc:

| Trường hợp | Kết quả ghi nhận | Ý nghĩa nghiệp vụ |
|---|---|---|
| Enbridge Scholarship | Hỗ trợ hai sinh viên thuộc các chương trình liên quan đến khối xây dựng và công nghệ; campus Ottawa; các kỳ Fall/Winter/Spring. Cột áp dụng cho sinh viên quốc tế để trống. | Phải lưu phạm vi chương trình và số suất riêng; ô trống không đủ cơ sở kết luận sinh viên quốc tế được hoặc không được nhận. |
| Henry Dzuba Bursary | Hỗ trợ theo nhu cầu tài chính cho sinh viên chương trình nghề thuộc khối xây dựng; campus Ottawa; cột quốc tế ghi YES. | Cần phân biệt bursary theo nhu cầu tài chính với học bổng thành tích, đồng thời lưu đối tượng quốc tế. |
| The Ronald Saumure Award of Excellence | Dành cho nhóm ngành Architectural Technician/Architectural Technology; có yêu cầu về phẩm chất, kỹ năng và đề cử của khoa; cho phép sinh viên quốc tế. | Tiêu chí lựa chọn không thể biểu diễn chỉ bằng một ngưỡng GPA. |

Các hàng minh họa ghi không yêu cầu đơn riêng nhưng vẫn hướng dẫn nộp qua cổng bursary trong ACSIS theo học kỳ. Vì vậy, “không có đơn riêng” không đồng nghĩa “không cần thao tác nộp hồ sơ”. Một trường hợp khác trên trang có tài trợ tái cấp đến $5,000 mỗi năm, kèm điều kiện cư trú/quốc tịch cụ thể; không được gán đặc tính này cho cả danh mục.

Kết quả chính là nhận diện nhu cầu lưu loại hỗ trợ, đối tượng, campus, kỳ áp dụng, ngành và hướng dẫn hồ sơ. **590 hàng không được diễn giải thành 590 học bổng quốc tế đã xác minh.**

#### 3.3.2. Brock University

Cả hai lần thử bằng requests và curl đều nhận **HTTP 403** tại trang dành cho sinh viên quốc tế kỳ 2026. Phản hồi được phân loại là bị chặn, không có HTML học bổng đủ điều kiện phân tích. Do đó, nghiên cứu này không ghi nhận số tiền, số bậc điểm, tiêu chí gia hạn hoặc deadline từ lần crawl Brock.

Kết quả thu được là bằng chứng về giới hạn truy cập của nguồn. Trường hợp này đòi hỏi cơ sở dữ liệu phân biệt “chưa thu thập được” với “không có học bổng”; không được tạo một bản ghi có giá trị 0 hoặc gia hạn bằng false để thay cho dữ liệu thiếu.

#### 3.3.3. Humber Polytechnic

Trang cung cấp **4 bảng và 14 hàng dữ liệu**, trong đó bảng học bổng đầu vào bậc degree có năm bậc rõ ràng:

| Điểm trung bình đầu vào | Giá trị công bố | Gia hạn ghi trong bảng |
|---|---:|---|
| Từ 95% | $4,000 | Có |
| 90–94.9% | $3,500 | Có |
| 85–89.9% | $3,000 | Có |
| 80–84.9% | $2,000 | Có |
| 75–79.9% | $1,500 | Cấp một lần |

Phần diễn giải của trang quy định các bậc đủ điều kiện được gia hạn nếu duy trì trung bình từ 80% trở lên. Không thể gán cùng một boolean gia hạn cho cả năm hàng.

Đối với người chuyển tiếp vào chương trình degree từ trường công lập, phần mô tả nêu mức $1,500 cho certificate và $2,500 cho diploma khi đáp ứng GPA từ 80%, cấp một lần. Một bảng khác thể hiện mức theo credential là $500, $750 và $1,000. Đây là những nhóm quyền lợi khác nhau; nghiên cứu không cộng hoặc gộp chúng thành một gói duy nhất.

Bảng thời gian còn phân biệt kỳ Summer 2026, Fall 2026, Winter 2027 và Summer 2027. Một số ô chỉ có ngày/tháng; việc chuẩn hóa năm phải căn cứ ngữ cảnh cụ thể của học kỳ, không tự gán năm crawl.

#### 3.3.4. International Business University — IBU

Trang có **7 bảng và 37 hàng được parser lưu**. Trong đó có bảng danh sách quốc gia, bảng chi phí và các nhóm học bổng khác nhau. Ba bảng chi phí được lưu đều thể hiện cấu trúc sau:

| Thành phần | Giá trị thể hiện | Phân loại trong nghiên cứu |
|---|---:|---|
| Giá trị học phí trước khấu trừ | $69,000 | Chi phí, không phải học bổng |
| Khoản International Scholarship được trừ | $9,000 | Khoản hỗ trợ cần gắn đúng chương trình/đối tượng |
| Khoản Regional Scholarship được trừ | $9,000 | Khoản hỗ trợ theo khu vực cần kiểm tra điều kiện |
| Tổng học phí sau khấu trừ | $51,000 | Chi phí còn phải trả, không phải tổng giá trị học bổng |

Phần văn bản còn có yêu cầu đặt cọc $5,625. Nếu chỉ lấy số nhỏ nhất/lớn nhất xuất hiện trên trang, kết quả sẽ lẫn học phí, khoản giảm trừ và tiền đặt cọc.

Trong phần Domestic, điều kiện nhận tiếp từ học kỳ thứ ba được diễn giải dựa trên GPA học kỳ từ 4.0 và tải học ít nhất 80%, với giới hạn tối đa tám học kỳ. Các điều kiện này không được gán sang nhóm International. Trang cũng có grant ghi hết hiệu lực vào cuối năm 2025; sự hiện diện của nội dung trên website tại ngày crawl không chứng minh grant còn áp dụng trong năm 2026.

Bố cục có các nhãn khu vực và phần nội dung dùng chung. Một số candidate theo heading chỉ chứa tên nhóm tiếp theo; vì vậy, **ranh giới heading do parser nhận diện chưa đủ để xác nhận một award hoàn chỉnh**. Kết quả nghiên cứu sử dụng bảng chi phí và đoạn điều kiện đã quan sát, đồng thời ghi nhận nhu cầu kiểm tra lại quan hệ giữa vùng nội dung, chương trình và quốc gia.

#### 3.3.5. Lakehead University

Trang công bố bảng học bổng đầu vào đại học cho intake **2027–2028**, có ba bậc:

| Điểm trung bình tương đương Canada | Điểm IB | Tổng giá trị trên nguồn | Phân bổ | Điều kiện gia hạn ghi nhận |
|---|---|---:|---|---|
| Từ 90% | Từ 35 | CAD 40,000 | CAD 10,000/năm, tối đa 4 năm | Duy trì 90% mỗi năm. Nếu điểm giảm xuống 80–89.9%, khoản nhận cho thời gian còn lại được điều chỉnh về CAD 7,500/năm. |
| 80–89.9% | 30–34 | CAD 30,000 | CAD 7,500/năm, tối đa 4 năm | Duy trì tối thiểu 80% mỗi năm. |
| 75–79.9% | 28–29 | CAD 6,000 | Chỉ năm đầu | Không gia hạn. |

Cả ba hàng ghi số lượng không giới hạn. Thời gian hưởng tối đa là bốn năm học hoặc đến khi được cấp bằng đầu tiên, tùy mốc nào đến trước. Các khoản trợ giảng sau đại học xuất hiện trên cùng trang thuộc nhóm hỗ trợ khác và không được đưa vào giá trị của học bổng đầu vào này.

Trường hợp Lakehead chứng minh một gói cần nhiều tier, mỗi tier có mức điểm, phân bổ tài chính và điều kiện gia hạn riêng. Chỉ lưu min/max chung sẽ làm mất sự khác biệt giữa khoản CAD 6,000 cấp một lần và các quyền lợi nhiều năm.

#### 3.3.6. MacEwan University

Trang không có bảng HTML, nhưng nội dung được tổ chức thành các nhóm heading cho **Canadian/domestic** và **International**. Nghiên cứu ghi nhận chuỗi Chancellor’s Scholarship Series với các bậc điểm; một số phần quốc tế còn sử dụng AGPA làm cách xét tương đương.

| Nhóm dữ kiện | Kết quả ghi nhận |
|---|---|
| Đối tượng | Domestic và international được trình bày thành các nhóm riêng. |
| Bậc thành tích | Có các ngưỡng 95–100%, 90–94.99%, 85–89.99% và 80–84.99%. |
| Gia hạn | Đoạn thuộc phần domestic đề cập Chancellor’s được gia hạn trong năm 2–4 nếu duy trì chương trình degree, GPA và tải học theo quy định. |
| Tải học/chi trả | Có yêu cầu 12 credits ở các kỳ liên quan và điều kiện nhận khoản chi trả tiếp theo. |
| Giá trị tiền | Output không xác định được mức tiền theo từng bậc; không có cơ sở điền số tiền vào bảng kết quả nghiên cứu. |

Kết quả cho thấy thiếu bảng HTML không đồng nghĩa thiếu dữ liệu học bổng. Mô hình cần lưu evidence theo nhóm đối tượng và điều kiện; không được lấy câu gia hạn ở vùng domestic rồi suy rộng cho mọi bậc international.

#### 3.3.7. Nipissing University

Cả requests và curl đều nhận **HTTP 403** tại trang Guaranteed Entrance Scholarships. Không thu được bảng học bổng hoặc điều kiện gia hạn từ lần crawl đang nghiên cứu. Các thông tin tài chính của Nipissing vì vậy được ghi nhận là **chưa xác định trong bộ dữ liệu này**.

Kết quả này không được thay thế bằng fixture tự dựng hoặc thông tin ghi nhớ từ nguồn khác. Nghiên cứu chỉ sử dụng phản hồi truy cập làm bằng chứng cho trạng thái thu thập.

#### 3.3.8. Queen’s University

Trang Financial Aid Overview không có bảng HTML về mức học bổng. Nội dung thu được chủ yếu mô tả cách phân bổ hỗ trợ tài chính vào tài khoản SOLUS:

| Nhóm hỗ trợ | Cách chi trả được mô tả |
|---|---|
| Admission, renewable, upper-year và exchange awards | Hỗ trợ cấp vào đầu năm học được phân thành hai đợt bằng nhau, gắn với thời điểm đóng tuition của các kỳ. |
| Queen’s General Bursary | Khoản cấp được đưa vào tài khoản trong cuối tháng 12 bằng một lần chi trả cho các kỳ đủ điều kiện của năm học. |
| Hoàn tiền | Một số trường hợp có thể được hoàn vào tài khoản ngân hàng sau khi trường kiểm tra lại tải học. |

Đây là quy định chi trả, không phải một deadline nộp hồ sơ và cũng không chứng minh tất cả award đều được gia hạn. Nghiên cứu chưa xác định giá trị tiền của một học bổng đầu vào cụ thể từ trang này. Mô hình cần tách tần suất chi trả, khả năng gia hạn và phương thức xét cấp.

#### 3.3.9. University of Alberta

Cả hai client nhận **HTTP 202** từ cơ chế WAF tại trang International Entrance Scholarships. Nội dung phản hồi không đủ điều kiện làm dữ liệu học bổng; không có bảng, tên gói hay mức tiền được xác nhận bởi lần crawl này.

HTTP 202 trong trường hợp này không được diễn giải thành “đã lấy được dữ liệu”. Nghiên cứu ghi nhận nguồn chưa thu thập được và không sử dụng thông tin tài chính từ fixture lịch sử để lấp chỗ trống.

#### 3.3.10. University of Lethbridge

Trang tổng quan có một bảng với sáu hàng được parser lưu, gồm một hàng tiêu đề được mã hóa bằng `td` và năm nhóm award. Các kết quả nghiệp vụ đọc được là:

| Nhóm award | Điều kiện hoặc giá trị ghi nhận | Đóng hồ sơ trên nguồn | Thông báo kết quả |
|---|---|---|---|
| Grade 11 Merit | Trung bình từ 80%: $800; 75–79.9%: $500 | Ngày 30/6 của năm học lớp 11 | Tháng 11 |
| Board of Governors’ Admission | Đã đăng ký admission; trung bình tuyển sinh cuối cùng từ 80%; xét tự động theo hồ sơ Fall | Ngày 15/12 | Tháng 5 |
| High School Awards | Tiêu chí tùy award: thành tích, nhu cầu tài chính, lãnh đạo, hoạt động, tài năng hoặc thư giới thiệu | Ngày 15/3 | Tháng 8 |
| Transfer Awards | Điều kiện thay đổi theo award | Ngày 15/6 | Tháng 8 |
| Undergraduate Awards | Điều kiện thay đổi theo award | Ngày 1/5 | Tháng 8 |

Các mốc không nêu năm được giữ dưới dạng ngày/tháng trong nghiên cứu. Không có bằng chứng đủ để kết luận khả năng gia hạn chung hoặc mức tiền cho các nhóm ngoài Grade 11 Merit. Mức $80,075 trong báo cáo cũ là lỗi ghép `$800` với phần điểm `75–79.9%`, không phải giá trị học bổng.

#### 3.3.11. University of Ottawa

Nghiên cứu nhận diện hai gói cho nhóm sinh viên bắt đầu từ Winter 2026 trở đi:

| Thuộc tính | International English Admission Scholarship | International English Academic Excellence Scholarship |
|---|---|---|
| Giá trị theo mô tả nguồn | $7,500/kỳ; nguồn đồng thời ghi $60,000 cho chương trình bốn năm | $10,000, thể hiện thành $5,000/kỳ |
| Số suất | Không giới hạn | 100 |
| Điểm tuyển sinh tối thiểu | 80% | 95% |
| Gia hạn | Có; nguồn ghi tối đa 12 lần cấp | Không |
| Phạm vi học | Undergraduate bằng tiếng Anh tại các khoa được liệt kê | Cùng nhóm khoa được liệt kê trên trang |
| Đối tượng | Sinh viên quốc tế có study permit, trả học phí quốc tế, học toàn thời gian | Sinh viên quốc tế đáp ứng điều kiện tương ứng |
| Kết hợp quyền lợi | Nguồn cho phép kết hợp với gói Academic Excellence | Nguồn cho phép kết hợp với gói Admission |

Các khoa được nêu gồm Arts, Engineering, Health Sciences, Science, Social Sciences và Telfer School of Management. French immersion không thuộc đối tượng nhận theo điều kiện được trình bày.

Một điểm cần làm rõ trước khi lập dự toán là nguồn đồng thời nêu **$7,500/kỳ, $60,000/bốn năm và tối đa 12 lần cấp**. Ba phát biểu được ghi nhận độc lập; không suy ra mọi sinh viên được trả đủ 12 lần hoặc tính thành $90,000. Điều khoản đầy đủ cần được đối chiếu trước khi chuẩn hóa lịch chi trả. Đây là lý do schema phải giữ nội dung nguyên bản bên cạnh trường giá trị có cấu trúc.

#### 3.3.12. University of Regina

Trang tổng quan có **4 bảng, 11 hàng được parser lưu**. Bốn hàng là tiêu đề được mã hóa bằng `td`; bảy hàng còn lại là các đợt mở/nộp hồ sơ. Kết quả đọc được:

| Nhóm / kỳ | Mở hồ sơ | Deadline | Thời điểm kết quả nếu nguồn nêu |
|---|---|---|---|
| Entrance awards | 15/01/2027 | 17/03/2027 | Tháng 6 |
| Chancellor’s | 01/10/2026 | 15/12/2026 | Tháng 5 |
| Continuing — Fall | 01/09/2026 | 04/10/2026 | Tháng 12 |
| Continuing — Winter | 05/01/2027 | 05/02/2027 | Tháng 4 |
| Continuing — Spring | 03/05/2027 | 03/06/2027 | Tháng 7 |
| Convocation — Fall | 01/09/2026 | 25/09/2026 | Không ghi trong bảng |
| Convocation — Spring | 09/03/2026 | 09/04/2026 | Không ghi trong bảng |

Nguồn giới thiệu SAMS để tra cứu và nộp hồ sơ. Một đoạn mô tả award có gia hạn và giới hạn $2,000 cho mỗi thành viên gia đình trong một năm học, nhưng không đủ cơ sở coi đó là mức trần của mọi học bổng Regina. Nghiên cứu ghi nhận được lịch hồ sơ theo nhóm, chưa xác định một dải tiền chung của trường.

Trường hợp này cho thấy một website có thể chứa cả kỳ quá khứ và tương lai trong cùng bảng tổng quan; điều kiện hiệu lực và kỳ tuyển sinh phải được xử lý ở mức offering.

#### 3.3.13. University of Waterloo

Trang có **9 bảng và 34 hàng dữ liệu**, đồng thời trình bày nhiều gói bằng heading. Các trường hợp tiêu biểu:

| Gói / nhóm | Giá trị và điều kiện ghi nhận | Ý nghĩa mô hình |
|---|---|---|
| President’s Scholarship of Distinction | Điểm từ 95%; $2,000 đầu vào, cùng khả năng tiếp cận khoản trải nghiệm quốc tế và nghiên cứu, mỗi khoản $1,500, theo điều kiện riêng | Phân biệt quyền lợi đầu vào với các khoản bổ sung có điều kiện; không cộng mặc định. |
| President’s Scholarship | Điểm 90–94.9%; $2,000, cấp một lần | Một award có tiêu chí điểm và trạng thái gia hạn riêng. |
| Merit Scholarship | Điểm 85–89.9%; $1,000, cấp một lần | Không gộp với President’s thành một mức tiền chung. |
| Jean Andrey Environment Leadership Scholarship | Tối đa $7,500 trong một năm; điểm đầu vào ít nhất 85%, quan tâm/lãnh đạo về môi trường; hạn trong bảng là 01/04/2027 | Cần lưu lĩnh vực áp dụng, tiêu chí phi học thuật, thời hạn và kỳ tuyển sinh. |
| Entrepreneurship Entrance Awards thuộc khối Engineering | Tối đa 30 suất, mỗi suất $10,000; có điều kiện ngành và hồ sơ đánh giá riêng | Số lượng award và giá trị mỗi suất là hai thuộc tính khác nhau. |

Một số nhóm chỉ dành cho các chương trình nhất định, một số ghi loại trừ một chương trình. Điều này cho thấy `school_wide` và danh sách ngành bao gồm chỉ là bước đầu; nếu sản phẩm cần lọc tự động theo ngoại lệ ngành thì phải bổ sung mô hình loại trừ có cấu trúc.

Các deadline trên trang thuộc những gói khác nhau. Không có cơ sở dùng một deadline hoặc một cờ “không gia hạn” để mô tả toàn bộ học bổng Waterloo.

### 3.4. Đánh giá mức độ đạt mục tiêu

Nghiên cứu đã thu thập được HTML hợp lệ của 10 trường, giữ nguyên các bảng và dữ kiện ngữ cảnh cần thiết để xác định mô hình trường–offering–tier–ngành–nguồn. Ba trường còn lại có bằng chứng về phản hồi bị chặn, nhưng chưa có kết quả nghiệp vụ từ lần crawl.

Từ 27 bảng và các phần nội dung không có bảng, nghiên cứu xác định được những biến thể chính: hỗ trợ cấp một lần, hỗ trợ tái cấp, quyền lợi nhiều năm, nhiều bậc thành tích, điều kiện theo ngành/đối tượng, thời hạn theo intake và hướng dẫn hồ sơ. Kết quả này đủ làm cơ sở đề xuất schema quan hệ. Tuy nhiên, 695 candidate vẫn là đơn vị cần rà soát; tổng số học bổng thực tế chưa được xác nhận và chưa có bản ghi được pipeline duyệt công bố.

Hai con số **695 hàng bảng** và **695 candidate** trùng nhau trong bộ dữ liệu hiện tại nhưng đo hai đại lượng khác nhau. Hàng bảng bao gồm bảng quốc gia, chi phí và một số tiêu đề bằng `td`; candidate còn bao gồm nhóm heading và các phần có thể chồng lặp. Không sử dụng sự trùng số này để suy ra số học bổng.

### 3.5. Cấu trúc dữ liệu của phiên bản nghiên cứu ban đầu

| Nhóm dữ liệu | Trường JSON | Giá trị sử dụng cho nghiên cứu/schema |
|---|---|---|
| Định danh nguồn | `school_name`, `slug`, `source_url` | Xác định trường và trang công bố. |
| Bằng chứng lấy trang | `crawl_metadata` | URL đích, HTTP thật, timestamp, hash, live/snapshot và lỗi. |
| Nội dung trang | `page_title`, `main_heading`, `sub_headings` | Xác định chủ đề và ranh giới vùng dữ liệu. |
| Bảng nguyên liệu | `tables_data[].headers/rows/cells/grid` | Giữ toàn bộ hàng, loại cell và span; phục vụ dựng lại bảng và duyệt tier. |
| Số tiền trong ngữ cảnh | `amounts_found`, `monetary_mentions` | Token thô và câu gốc; chưa phải min/max của học bổng. |
| Điều kiện | `renewal_evidence`, `eligibility_evidence`, `deadline_evidence` | Bằng chứng dùng khi duyệt và ánh xạ điều kiện. |
| Mục cần duyệt | `scholarship_candidates` | Tên hoặc nhóm/tier dự kiến, evidence, ngữ cảnh heading, loại candidate. |

Các trường `min_amount_cad`, `max_amount_cad`, `is_renewable`, `duration_note`, `eligibility_criteria`, `deadlines` ở cấp trang hiện để `null` có chủ đích. Không có một giá trị chung đáng tin cậy cho toàn bộ các gói xuất hiện trên trang.


## 4. Phát hiện từ dữ liệu thực tế → yêu cầu thiết kế

### 4.1. Một trường có nhiều gói học bổng

Kết quả khảo sát uOttawa ở mục 3.3.11 phân biệt International English Admission Scholarship và International English Academic Excellence Scholarship. Hai gói có trạng thái gia hạn khác nhau; các nhóm intake cũ cũng xuất hiện trên cùng trang.

**Yêu cầu thiết kế:** một trường liên kết với nhiều `scholarships`. Một bản ghi scholarship đại diện cho một gói học bổng; các kỳ áp dụng và điều kiện theo kỳ được ghi trong `requirements`, không tạo một học bổng đại diện cho toàn trường. Tên heading chung hoặc `section_group` không được tự động nhập như một gói độc lập.

### 4.2. Một gói có nhiều bậc điểm và quy tắc gia hạn

Bảng Lakehead được trình bày đầy đủ ở mục 3.3.5. Dưới đây là cấu trúc hàng dữ liệu được sử dụng để phân tích mô hình tier:

| Academic average | IB average | Giá trị thể hiện trong bảng | Số lượng |
|---|---|---|---|
| 90.0%+ | 35+ | $40,000 ($10,000 x 4 years) 1 | Unlimited |
| 80.0% - 89.9% | 30-34 | $30,000 ($7,500 x 4 years) 2 | Unlimited |
| 75.0% - 79.9% | 28-29 | $6,000 ($6,000 in Year 1 only) 3 | Unlimited |

Các footnote trên trang phân biệt bậc gia hạn và bậc chỉ cấp năm đầu; lời kể sinh viên không thể thay thế điều kiện chính thức. Khoản trợ giảng sau đại học cũng xuất hiện trên trang nhưng là loại hỗ trợ khác.

**Yêu cầu thiết kế:** giữ điều kiện từng bậc và kỳ tính tiền trong phần mô tả quyền lợi. Không gán cùng một cờ gia hạn hoặc một dải tiền cho mọi hàng của bảng.

### 4.3. Số tiền xuất hiện trên trang chưa chắc là giá trị học bổng

Kết quả khảo sát IBU cho thấy các bảng tuition và câu ngữ cảnh có cả học phí trước/sau khấu trừ và tiền đặt cọc. Giá trị $69,000 không thể tự động trở thành mức trần học bổng. Các vùng Domestic và International, cùng thông tin grant hết hiệu lực, cần được đọc riêng.

Kết quả khảo sát Lethbridge cho thấy mức tiền và mức điểm nằm sát nhau trong DOM. Parser phải giữ dấu cách để không biến `$800` đứng trước `75–79.9%` thành `$80,075`.

**Yêu cầu thiết kế:** chỉ ghi giá trị sau khi xác định đúng quyền lợi, tiền tệ và kỳ cấp từ nguồn. Trình bày rõ trong `value_text`, giữ link `source_url` để đối chiếu; không lấy min/max mọi con số trên trang làm giá trị học bổng.

### 4.4. Đối tượng áp dụng và phạm vi ngành là dữ liệu nghiệp vụ

Bảng danh mục Algonquin có các cột `Open to International?`, `Term`, `Application Required?`, mô tả ngành và campus. Nội dung MacEwan phân biệt Domestic và International.

**Yêu cầu thiết kế:** ghi đối tượng, bậc học, điều kiện và phạm vi ngành trong `requirements`; người xem mở `source_url` để đọc hướng dẫn nộp. Ô trống ở `Open to International?` là chưa xác định, không tự chuyển thành `false` hoặc coi là đủ điều kiện đưa vào danh mục international entrance.

### 4.5. Kỳ tuyển sinh, thời hạn và lịch chi trả phải được giữ riêng

Trang Lakehead có nhãn intake; uOttawa có các nhóm kỳ bắt đầu khác nhau; IBU có nội dung grant ghi thời điểm hết hiệu lực. Một số trang đồng thời nêu tiền theo kỳ, tổng toàn khóa và số lần trả tối đa.

**Yêu cầu thiết kế:** giữ các kỳ áp dụng trong `requirements`, hạn nộp trong `deadline`; người xem mở `source_url` để đọc cách nộp. Không coi deadline là kỳ nhập học. Không suy ra lịch chi trả bằng phép nhân khi các phát biểu trên nguồn chưa được làm rõ.

### 4.6. Giữ link nguồn chính thức

Nội dung crawl có thể thiếu điều kiện hoặc bị chặn. Mỗi học bổng giữ URL nguồn để người xem đối chiếu điều khoản mới nhất và tìm hiểu cách nộp. Schema hiển thị không lưu thời điểm crawl. Thông tin chưa rõ để trống, không tự suy diễn thành điều kiện hoặc quyền lợi đã được xác nhận.

## 5. Thiết kế schema tinh gọn

### 5.1. Thông tin người tìm học bổng cần biết

Thiết kế tập trung vào các câu hỏi: học bổng gì, của trường nào, dành cho ai, được hỗ trợ bao nhiêu, cần đáp ứng điều kiện gì, áp dụng cho ngành/kỳ nào, hạn khi nào và có được gia hạn không. Người dùng bấm URL nguồn để tìm hiểu cách nộp và điều khoản đầy đủ.

Giữ hai bảng:

| Bảng | Vai trò |
|---|---|
| `schools` | Tên và mã trường. Một trường có nhiều học bổng. |
| `scholarships` | Thông tin cần đọc để cân nhắc và đăng ký một học bổng. |

Không tách bảng ngành, bảng nối ngành hoặc bảng tier trong phạm vi hiện tại. Các mức quyền lợi theo điểm được trình bày trong `value_text`; mọi điều kiện được ghi chung trong `requirements`. Không lưu thêm workflow duyệt/công bố, người duyệt, khóa offering, bản dịch song song hoặc bản sao bằng chứng HTML trong schema này.

### 5.2. Các field cần giữ

**Bảng `schools`:**

| Field | Ý nghĩa |
|---|---|
| `id` | ID nội bộ, tự sinh. |
| `name` | Tên trường. |
| `slug` | Mã trường duy nhất, khớp cách đặt tên trong crawler. |

**Bảng `scholarships`:**

| Field | Người xem cần biết gì? |
|---|---|
| `id` | ID nội bộ để mở/cập nhật bản ghi. |
| `school_id` | Học bổng của trường nào? |
| `name` | Tên học bổng là gì? |
| `type` | Scholarship, bursary hay award? |
| `value_text` | Được bao nhiêu hoặc quyền lợi gì? Ghi rõ kỳ cấp và từng mức theo điểm. |
| `requirements` | Toàn bộ điều kiện của học bổng: đối tượng, quốc tịch, bậc học, ngành/khoa, kỳ áp dụng, điểm, ngoại ngữ, chuyển tiếp, học toàn thời gian, điều kiện nhận một lần hoặc gia hạn. |
| `deadline` | Hạn đăng ký là khi nào? |
| `source_url` | Link nguồn chính thức để đọc chi tiết và hướng dẫn nộp. |
| `updated_at` | Lần cập nhật bản ghi gần nhất trong hệ thống, có múi giờ. |
| `updated_by` | Định danh người hoặc script cập nhật; NULL nếu chưa biết. |

Các trường nội dung ngoài ID, liên kết trường, tên và URL nguồn có thể để `NULL` nếu nguồn chưa xác nhận. `updated_at` bắt buộc có; `updated_by` có thể NULL khi chưa biết người/script cập nhật. Thiếu dữ liệu không có nghĩa là không giới hạn.

`updated_at` được đặt mặc định khi tạo bản ghi; khi sửa nội dung, ứng dụng hoặc ingestion phải cập nhật đồng thời `updated_at` và `updated_by`. Ví dụ định danh script: `crawler:fleming_college`; nếu người dùng sửa, dùng ID tài khoản từ hệ thống quản trị. `updated_by` hiện là TEXT, chưa gắn bảng người dùng. Hai field chỉ theo dõi lần sửa bản ghi gần nhất, không thay cho thời điểm cập nhật trang nguồn và không lưu toàn bộ lịch sử.

Phạm vi danh mục mục tiêu là học bổng entrance có nhận sinh viên quốc tế, kể cả transfer entrance khi nguồn cho phép. Đây là điều kiện chọn dữ liệu ở bước crawl/chuẩn hóa, không cần hai field phân loại riêng trong database. Output hiện tại vẫn có mục domestic/continuing; cần lọc lại trước khi nhập vào danh mục này. Không được hiểu rằng dữ liệu cũ đã đáp ứng phạm vi mới.

`requirements` là một field `TEXT`, có thể trình bày thành các gạch đầu dòng khi hiển thị. Ví dụ cách tổ chức nội dung (chỉ điền thông tin được nguồn xác nhận):

- Đối tượng, quốc tịch và điều kiện về quá trình học trước đó.
- Bậc học, chương trình/ngành và kỳ nhập học áp dụng.
- Điểm học tập, ngoại ngữ và các tiêu chí tuyển chọn.
- Điều kiện học toàn thời gian, thư xác nhận hoặc đặt cọc nếu có.
- Điều kiện nhận một lần hoặc tiếp tục nhận/gia hạn, ghi đúng từng mức quyền lợi.

Luồng hiển thị dự kiến: người dùng chọn trường, chọn ngành, đọc học bổng của trường và tự đối chiếu điều kiện; muốn tìm hiểu cách nộp thì mở `source_url`. Hạn nộp giữ riêng trong `deadline` để cân nhắc ngay khi xem danh sách. Chọn ngành chưa tự động lọc học bổng theo ngành vì phạm vi ngành hiện nằm trong text. Chỉ bổ sung liên kết ngành riêng nếu sản phẩm cần lọc chính xác sau này.

### 5.3. Ví dụ cách ghi quyền lợi

Với Lakehead, `value_text` có thể trình bày:

- Điểm từ 90%: 10.000 CAD/năm, tổng tối đa 40.000 CAD trong bốn năm.
- Điểm 80–89,9%: 7.500 CAD/năm, tổng tối đa 30.000 CAD trong bốn năm.
- Điểm 75–79,9%: 6.000 CAD cho năm đầu, không gia hạn.

Điều kiện gia hạn theo từng mức ghi trong `requirements`, không gom thành một quy tắc chung sai cho mọi mức.

Với Fleming, `value_text` giữ quyền lợi `up to $3,200`. `requirements` ghi các kỳ `Fall 2026`/`Winter 2027`, các loại văn bằng được xét, điều kiện nhận một lần, có thư xác nhận và học toàn thời gian. Không tự đổi `$` thành CAD nếu nội dung hiện hành chưa xác nhận.

Thiết kế này phục vụ đọc và tra cứu. Vì giá trị được giữ dạng text, chưa hỗ trợ so sánh số tiền tự động hoặc lọc chính xác theo từng tier; chỉ bổ sung cột số khi sản phẩm thực sự cần chức năng đó.

### Ví dụ bản ghi hiển thị: Fleming College

Ví dụ dưới đây trình bày lại nội dung trong `outputs/fleming_college.json`, chưa phải dữ liệu đã nhập database. `id` do database sinh, `school_id` lấy từ trường Fleming trong bảng `schools`.

```json
{
  "name": "Entry Scholarship",
  "type": "scholarship",
  "value_text": "Tối đa $3.200, hỗ trợ học phí, nhận một lần.",
  "requirements": "- Sinh viên quốc tế đăng ký chương trình certificate, diploma, advanced diploma hoặc graduate certificate.\n- Áp dụng cho Fall 2026 và Winter 2027.\n- Phải được chấp thuận, có thư xác nhận học bổng và nhập học toàn thời gian.\n- Chỉ được nhận một lần; việc cấp học bổng phụ thuộc số suất còn lại.",
  "deadline": null,
  "source_url": "https://flemingcollege.ca/scholarships-for-international-students"
}
```

Không có hạn nộp được xác nhận nên `deadline` để NULL. URL nguồn vẫn là nơi người dùng đọc điều khoản đầy đủ. Các field `updated_at`/`updated_by` được bên ghi database cung cấp khi tạo hoặc sửa bản ghi; ví dụ nội dung từ crawler ở trên không tự xác nhận đã có lần ghi database nào.

### 5.4. DDL PostgreSQL

Đây là DDL tham khảo đã rút gọn, chưa áp dụng vào database của portal. Không dùng trực tiếp để xóa hoặc thay đổi các bảng đang chạy.

```sql
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
```

## 6. Ánh xạ kết quả crawl vào schema

| Dữ liệu trong JSON hiện tại | Field database | Cách xử lý |
|---|---|---|
| `school.name`, `school.slug` | `schools.name`, `schools.slug` | Tra cứu trường theo slug. |
| Tên từng học bổng | `scholarships.name` | Mỗi học bổng thực là một bản ghi; nhóm danh mục chưa có các suất cụ thể không tự coi là một học bổng. |
| `type` | `type` | Giữ loại scholarship/bursary/award nếu biết. |
| `value_text`, `value_texts`, `values`, `tiers`, `benefits` | `value_text` | Trình bày quyền lợi có điều kiện, tiền tệ và kỳ cấp rõ ràng; không cộng các khoản khác cơ sở tính. |
| `eligibility`, `applicant_category`, `eligible_stages`, `study_level`, `programs`, `intakes`, `renewable`, `renewal_conditions` và điều kiện riêng trong tier | `requirements` | Gộp thành nội dung dễ đọc, giữ điều kiện từng mức; không tự thêm thông tin còn thiếu. |
| Deadline của học bổng | `deadline` | Giữ dạng chữ, không tự điền thời gian còn thiếu. |
| `scholarship.source_url` hoặc `source_url` của file | `source_url` | Ưu tiên link riêng của gói; nếu không có dùng link nguồn cấp file. |
| Thao tác ghi/cập nhật từ ứng dụng hoặc ingestion | `updated_at`, `updated_by` | Ghi thời điểm thao tác và người/script thực hiện; không sao chép thời điểm crawl thành thời điểm sửa bản ghi. |

Quy tắc cập nhật bản ghi (để bên tích hợp thực hiện): khi INSERT, dùng mặc định thời gian và cung cấp định danh người/script; khi UPDATE nội dung, ghi lại cả hai field. Ví dụ câu lệnh có tham số:

```sql
UPDATE scholarships
SET requirements = $2,
    updated_at = CURRENT_TIMESTAMP,
    updated_by = $3
WHERE id = $1;
```

`$1` là ID học bổng, `$2` là nội dung điều kiện mới, `$3` là ID người hoặc tên script thực hiện. Không dùng `fetched_at` của JSON làm `updated_at`, không ghi tên người duyệt khi người đó không thực hiện cập nhật.

Đây là quy tắc ánh xạ đề xuất, chưa có script nhập database tự động. Crawler vẫn giữ cấu trúc JSON v4 hiện tại; lần tinh gọn này chỉ thay thiết kế database và phần mô tả tương ứng.

## 7. Giới hạn và hướng hoàn thiện

- Các kết quả nghiên cứu ở phần trước phản ánh đợt thu thập ban đầu; kết quả crawl mới xem trong `outputs/`.
- Điều kiện nằm trong footnote, trang liên kết hoặc nguồn bị chặn vẫn cần được đối chiếu; không dựng dữ liệu thay thế.
- Schema tinh gọn ưu tiên thông tin để đọc, chưa phục vụ tự động tính mức học bổng hoặc khẳng định ứng viên đủ điều kiện.
- Giữ link nguồn và thông tin lần sửa bản ghi gần nhất (`updated_at`, `updated_by`); không lưu thời điểm crawl hay toàn bộ lịch sử thay đổi. Người xem mở nguồn để kiểm tra điều khoản mới nhất.
- Chưa có ETL nhập JSON vào database và chưa triển khai schema vào LOA Portal.

## 8. Kết luận nghiên cứu

Nghiên cứu đạt mục tiêu xác định những dạng dữ liệu thực tế cần quản lý cho bài toán học bổng tại LOA Portal. Kết quả của 10 nguồn truy cập được cho thấy ít nhất ba lớp thông tin phải tách biệt: trang/bằng chứng nguồn, gói theo kỳ tuyển sinh và bậc quyền lợi theo điều kiện. Các trường hợp Humber và Lakehead chứng minh sự khác nhau giữa cấp một lần và gia hạn; uOttawa thể hiện nhiều gói có điều kiện và lịch cấp khác nhau; IBU cho thấy rủi ro lẫn chi phí với quyền lợi; Algonquin và Waterloo thể hiện phạm vi ngành và tiêu chí lựa chọn đa dạng; Regina và Lethbridge cung cấp lịch hồ sơ theo nhóm; MacEwan và Queen’s cho thấy dữ liệu có thể được trình bày bằng văn bản thay vì bảng tài chính.

Thiết kế hiện tại được rút về hai bảng `schools` và `scholarships`, tập trung vào thông tin người tìm học bổng cần đọc: quyền lợi, đối tượng, điều kiện, kỳ nhập học, hạn nộp và gia hạn. URL nguồn được giữ để đối chiếu và đọc hướng dẫn nộp; `updated_at`/`updated_by` ghi nhận lần sửa bản ghi gần nhất. Đây là schema tham khảo; chưa có bước tự động nhập JSON hoặc triển khai vào database portal.
