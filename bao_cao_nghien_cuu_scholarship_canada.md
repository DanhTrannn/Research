# BÁO CÁO NGHIÊN CỨU DỮ LIỆU HỌC BỔNG CANADA VÀ THIẾT KẾ SCHEMA CHO LOA PORTAL

> **Ghi chú tổ chức mã nguồn:** báo cáo ghi nhận đợt nghiên cứu trước khi tinh gọn repo. Mã hiện tại dùng `run_all.py`, `pipeline.py`, mỗi trường một file trong `schools/` và một JSON tự chứa bằng chứng trong `outputs/`. Script, log và dữ liệu trung gian cũ đã được lưu trong bản sao ngoài repo `../Scholarship-backup-20261106-101222.tar.gz`.


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

### 2.2. Phương pháp nghiên cứu

Quy trình thực hiện theo thứ tự:

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

Fixture cũ không có bằng chứng nguồn được lưu riêng tại kho lịch sử (tài liệu lịch sử trong bản sao lưu). Crawler không dùng các file này làm fallback. Snapshot mới chỉ được phép dùng khi bật `--allow-snapshot`, metadata/hash khớp và bản lưu không quá 7 ngày.

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

### 3.5. Cấu trúc dữ liệu thu được

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

**Yêu cầu thiết kế:** một trường liên kết với nhiều `scholarships`. Một bản ghi scholarship đại diện cho một offering theo kỳ/phiên bản, không đại diện cho toàn trường. Tên heading chung hoặc `section_group` không được tự động nhập như một gói độc lập.

### 4.2. Một gói có nhiều bậc điểm và quy tắc gia hạn

Bảng Lakehead được trình bày đầy đủ ở mục 3.3.5. Dưới đây là cấu trúc hàng dữ liệu được sử dụng để phân tích mô hình tier:

| Academic average | IB average | Giá trị thể hiện trong bảng | Số lượng |
|---|---|---|---|
| 90.0%+ | 35+ | $40,000 ($10,000 x 4 years) 1 | Unlimited |
| 80.0% - 89.9% | 30-34 | $30,000 ($7,500 x 4 years) 2 | Unlimited |
| 75.0% - 79.9% | 28-29 | $6,000 ($6,000 in Year 1 only) 3 | Unlimited |

Các footnote trên trang phân biệt bậc gia hạn và bậc chỉ cấp năm đầu; lời kể sinh viên không thể thay thế điều kiện chính thức. Khoản trợ giảng sau đại học cũng xuất hiện trên trang nhưng là loại hỗ trợ khác.

**Yêu cầu thiết kế:** tách `scholarship_tiers`, giữ điều kiện từng bậc, kỳ tính tiền và evidence. Không gán cùng một cờ gia hạn hoặc một dải tiền cho mọi hàng của bảng.

### 4.3. Số tiền xuất hiện trên trang chưa chắc là giá trị học bổng

Kết quả khảo sát IBU cho thấy các bảng tuition và câu ngữ cảnh có cả học phí trước/sau khấu trừ và tiền đặt cọc. Giá trị $69,000 không thể tự động trở thành mức trần học bổng. Các vùng Domestic và International, cùng thông tin grant hết hiệu lực, cần được đọc riêng.

Kết quả khảo sát Lethbridge cho thấy mức tiền và mức điểm nằm sát nhau trong DOM. Parser phải giữ dấu cách để không biến `$800` đứng trước `75–79.9%` thành `$80,075`.

**Yêu cầu thiết kế:** chỉ nhập giá trị tài chính sau khi xác định loại quyền lợi, currency và `payment_basis`. Giữ `value_display_text` và bằng chứng gốc; không map trực tiếp `min/max(amounts_found)` vào CSDL học bổng.

### 4.4. Đối tượng áp dụng và phạm vi ngành là dữ liệu nghiệp vụ

Bảng danh mục Algonquin có các cột `Open to International?`, `Term`, `Application Required?`, mô tả ngành và campus. Nội dung MacEwan phân biệt Domestic và International.

**Yêu cầu thiết kế:** lưu `applicant_category`, `application_method`, `study_level`, điều kiện và phạm vi chương trình. Ô trống ở `Open to International?` là chưa xác định, không tự chuyển thành `false`. Khi chỉ áp dụng cho một số ngành, dùng quan hệ N–N với `programs`.

### 4.5. Kỳ tuyển sinh, thời hạn và lịch chi trả phải được giữ riêng

Trang Lakehead có nhãn intake; uOttawa có các nhóm kỳ bắt đầu khác nhau; IBU có nội dung grant ghi thời điểm hết hiệu lực. Một số trang đồng thời nêu tiền theo kỳ, tổng toàn khóa và số lần trả tối đa.

**Yêu cầu thiết kế:** định danh offering bằng `intake_key`; lưu `valid_from/valid_until`, deadline và phương thức nộp riêng. Không coi deadline là ngày hết hiệu lực. Không suy ra lịch chi trả bằng phép nhân khi các phát biểu trên nguồn chưa được làm rõ.

### 4.6. Cần tách thu thập bằng chứng khỏi duyệt/công bố

Ba nguồn bị chặn không cung cấp được HTML học bổng trong lần chạy này. Với nguồn lấy được, candidate còn có thể trùng giữa heading và bảng, thiếu footnote hoặc chưa xác định currency/kỳ tính tiền.

**Yêu cầu thiết kế:** lưu URL nguồn, thời điểm lấy dữ liệu và evidence trực tiếp trong `scholarships`, cùng trạng thái duyệt. Chỉ công bố bản ghi đã được duyệt; giá trị chưa xác định giữ `null` hoặc `unknown`.

## 5. Thiết kế schema quan hệ đề xuất

### 5.1. Nguyên tắc và các thực thể

Schema ưu tiên truy xuất nguồn và thể hiện đúng nghiệp vụ đã quan sát được. Đây là thiết kế tham chiếu, chưa phải khẳng định tối ưu cho mọi chức năng tương lai của LOA Portal.

| Bảng | Đơn vị bản ghi | Quan hệ chính |
|---|---|---|
| `schools` | Một trường | 1–N với `programs`, `scholarships`. |
| `programs` | Một chương trình thuộc trường | N–N với `scholarships` qua `scholarship_programs`. |
| `scholarships` | Một gói học bổng theo intake/phiên bản | Thuộc một trường, lưu URL nguồn trực tiếp, có nhiều tier. |
| `scholarship_tiers` | Một bậc/biến thể giá trị của offering | N–1 với `scholarships`. |
| `scholarship_programs` | Một liên kết gói học bổng–ngành | Khóa chính kép; hai đầu bắt buộc cùng trường. |

### 5.2. Từ điển dữ liệu

#### A. Trường và chương trình

| Bảng / cột | Kiểu | Ý nghĩa và ràng buộc |
|---|---|---|
| `schools.id` | `BIGINT IDENTITY` | PK nội bộ của trường. |
| `schools.name_en` | `TEXT` | Tên tiếng Anh, bắt buộc. |
| `schools.slug` | `TEXT` | Định danh trường duy nhất. |
| `programs.id` | `BIGINT IDENTITY` | PK của chương trình. |
| `programs.school_id` | `BIGINT` | FK tới trường sở hữu. |
| `programs.name_en` | `TEXT` | Tên chương trình, bắt buộc. |

Khi tích hợp với LOA Portal, dùng bảng trường/ngành hiện có nếu phù hợp; không tạo bản sao các trường và chương trình đang tồn tại.

Nguồn được lưu trực tiếp trên mỗi bản ghi `scholarships` bằng `source_url` và `source_fetched_at`. Thiết kế này không cần bảng nguồn hoặc khóa ngoại tới bản chụp HTML. `source_fetched_at` có thể NULL nếu chưa rõ thời điểm thu thập; không dùng thời điểm insert thay cho thời điểm lấy nguồn.

HTML, hash và lịch sử HTTP vẫn được giữ trong bộ output crawl để phục vụ đối chiếu. Cơ sở dữ liệu nghiệp vụ không quản lý một danh mục lịch sử bản chụp riêng; nếu nhiều gói dùng chung URL thì mỗi gói lưu URL đó.

#### B. `scholarships` — offering của một gói học bổng

| Nhóm | Các cột và kiểu | Ý nghĩa |
|---|---|---|
| Định danh | `id BIGINT`, `school_id BIGINT`, `external_key TEXT`, `intake_key TEXT` | Một offering duy nhất theo `(school_id, external_key, intake_key)`. `external_key` do bước chuẩn hóa quản lý, không dùng thứ tự candidate làm định danh bền vững. |
| Tên hiển thị | `name_en TEXT`, `name_vi TEXT` | Tên gói và bản dịch; không lấy tên trường làm tên học bổng. |
| Nguồn | `source_url TEXT`, `source_fetched_at TIMESTAMPTZ`, `evidence_json JSONB`, `raw_tables_json JSONB` | Link công bố, thời điểm lấy nguồn và bằng chứng đã chọn đúng vùng/award. |
| Gia hạn | `is_renewable BOOLEAN`, `duration_note_en TEXT`, `duration_note_vi TEXT` | Quy tắc chung nếu có; có thể unknown khi phụ thuộc tier. |
| Đối tượng | `program_scope TEXT`, `applicant_category TEXT`, `study_level TEXT`, `eligibility_criteria TEXT` | Phạm vi ngành, domestic/international, bậc học và yêu cầu. |
| Hồ sơ | `application_method TEXT`, `deadline_text TEXT`, `deadline_at TIMESTAMPTZ` | Phương thức xét/nộp, nguyên văn deadline và thời điểm chuẩn hóa nếu xác định được. |
| Hiệu lực | `valid_from DATE`, `valid_until DATE` | Khoảng hiệu lực của offering; không đồng nhất với ngày nộp hồ sơ. |
| Duyệt/công bố | `verification_status TEXT`, `reviewed_by TEXT`, `reviewed_at TIMESTAMPTZ`, `published BOOLEAN` | Trạng thái duyệt và thông tin người duyệt. |
| Theo dõi thay đổi | `created_at`, `updated_at TIMESTAMPTZ` | Thời gian tạo/cập nhật; `updated_at` có trigger. |

Các enum nghiệp vụ trong DDL:

- `program_scope`: `unknown`, `school_wide`, `selected_programs`.
- `applicant_category`: `unknown`, `domestic`, `international`, `both`.
- `application_method`: `unknown`, `automatic`, `application_required`, `nomination`.
- `verification_status`: `needs_review`, `verified`, `rejected`.

#### C. `scholarship_tiers` — bậc và giá trị

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| `id`, `scholarship_id` | `BIGINT` | PK và FK tới offering. |
| `tier_key` | `TEXT` | Khóa bậc duy nhất trong một scholarship. |
| `eligibility_text` | `TEXT` | Điều kiện bậc điểm/đối tượng; giữ nguyên khi chưa đủ thông tin cấu trúc hóa GPA. |
| `is_renewable`, `renewal_conditions` | `BOOLEAN`, `TEXT` | Gia hạn và điều kiện riêng của bậc. |
| `value_kind` | `TEXT` | `money`, `tuition_percentage`, `tuition_waiver`, `unknown`. |
| `min_value`, `max_value` | `NUMERIC(14,2)` | Giá trị theo đúng loại và kỳ tính; không trộn năm/kỳ/toàn khóa. |
| `currency` | `CHAR(3)` | Mã tiền tệ khi `value_kind = money`; không suy ra CAD chỉ từ dấu `$`. |
| `payment_basis` | `TEXT` | `unknown`, `one_time`, `per_term`, `per_year`, `total_degree`. |
| `max_instalments` | `INTEGER` | Số lần cấp tối đa đã được nguồn xác nhận. |
| `tuition_rate_basis` | `TEXT` | `domestic`, `international`, `unknown` cho quyền lợi theo tuition. |
| `value_display_text` | `TEXT` | Cách thể hiện giá trị gốc, bao gồm các ghi chú chưa chuẩn hóa hết. |
| `evidence_text` | `TEXT` | Bằng chứng cụ thể của bậc/giá trị, bắt buộc không rỗng. |

Ví dụ ánh xạ **đề xuất để duyệt** từ bảng Lakehead: bậc 90%+ có thể lưu `value_kind = money`, `currency = CAD`, `min_value = max_value = 10000`, `payment_basis = per_year`, tối đa 4 lần cấp; nguyên văn tổng $40,000 vẫn nằm trong `value_display_text`. Bậc $6,000 năm đầu có `payment_basis = one_time`, `is_renewable = false`. Đây là minh họa mô hình, chưa phải bản ghi đã insert hoặc đã duyệt công bố.

#### D. `scholarship_programs` — phạm vi ngành

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| `scholarship_id` | `BIGINT` | Một đầu của PK kép, FK tới offering. |
| `program_id` | `BIGINT` | Một đầu của PK kép, FK tới chương trình. |
| `school_id` | `BIGINT` | Dùng trong hai FK kép để buộc học bổng và ngành cùng trường. |

`school_id` ở bảng nối là phần dư được giữ có chủ đích để kiểm soát toàn vẹn bằng FK kép. Không lấy việc có FK làm bằng chứng rằng mọi quy tắc nghiệp vụ đã được đảm bảo.

### 5.3. Ràng buộc và quy tắc nhập dữ liệu

| Ràng buộc / quy tắc | Cách thực hiện |
|---|---|
| Không nhập trùng offering cùng intake | `UNIQUE (school_id, external_key, intake_key)`. |
| Nguồn công bố không rỗng | `source_url NOT NULL` và CHECK chuỗi có nội dung. |
| Học bổng và ngành cùng trường | Hai FK kép tại `scholarship_programs`. |
| Không có số âm hoặc min > max | Các `CHECK` trên `scholarship_tiers`. |
| Phần trăm hợp lệ và có rate basis | `CHECK` loại quyền lợi, khoảng phần trăm và cơ sở tuition. |
| Không làm mất unknown | `is_renewable` cho phép NULL; scope/category/method mặc định `unknown`. |
| Khoảng hiệu lực hợp lệ | `valid_from <= valid_until` khi có đủ hai mốc. |
| Duyệt trước khi công bố | `published` yêu cầu `verified` và phạm vi đã xác định; trạng thái verified yêu cầu reviewer/thời gian duyệt. |
| Cập nhật thời gian thật | Trigger cập nhật `updated_at` khi UPDATE. |

Một số việc phải do bước duyệt/ứng dụng thực hiện: xác nhận điều kiện và currency, kiểm tra đủ liên kết ngành khi `selected_programs`, xác định intake, phân loại award/bursary và bảo đảm evidence đúng gói. Các CHECK hiện có không tự chứng minh các điều này.

### 5.4. DDL PostgreSQL

DDL dưới đây đặc tả đầy đủ năm bảng, quan hệ và ràng buộc được đề xuất. Schema đã được thực thi thành công trên PostgreSQL tạm; chưa triển khai vào LOA Portal. Bản SQL độc lập được lưu kèm để tái lập triển khai.

```sql
-- PostgreSQL 16+. Standalone reference schema; adapt schools/programs to the portal
-- before applying to an existing database. No automatic ingestion of crawler candidates.
BEGIN;

CREATE TABLE schools (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name_en TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE
);
CREATE TABLE programs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    school_id BIGINT NOT NULL REFERENCES schools(id),
    name_en TEXT NOT NULL,
    UNIQUE (id, school_id)
);
-- One offering for a named award and intake/version; never a whole school page.
CREATE TABLE scholarships (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    school_id BIGINT NOT NULL REFERENCES schools(id),
    external_key TEXT NOT NULL,
    intake_key TEXT NOT NULL,
    name_en TEXT NOT NULL,
    name_vi TEXT,
    source_url TEXT NOT NULL CHECK (length(trim(source_url)) > 0),
    source_fetched_at TIMESTAMPTZ, -- NULL when the collection time is unknown.
    is_renewable BOOLEAN, -- NULL means unknown; never defaults to FALSE.
    duration_note_en TEXT,
    duration_note_vi TEXT,
    program_scope TEXT NOT NULL DEFAULT 'unknown'
        CHECK (program_scope IN ('unknown', 'school_wide', 'selected_programs')),
    applicant_category TEXT NOT NULL DEFAULT 'unknown'
        CHECK (applicant_category IN ('unknown', 'domestic', 'international', 'both')),
    study_level TEXT,
    eligibility_criteria TEXT,
    application_method TEXT NOT NULL DEFAULT 'unknown'
        CHECK (application_method IN ('unknown', 'automatic', 'application_required', 'nomination')),
    deadline_text TEXT,
    deadline_at TIMESTAMPTZ,
    valid_from DATE,
    valid_until DATE,
    evidence_json JSONB NOT NULL CHECK (jsonb_typeof(evidence_json) = 'object' AND evidence_json <> '{}'::jsonb),
    raw_tables_json JSONB,
    verification_status TEXT NOT NULL DEFAULT 'needs_review'
        CHECK (verification_status IN ('needs_review', 'verified', 'rejected')),
    reviewed_by TEXT,
    reviewed_at TIMESTAMPTZ,
    published BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (school_id, external_key, intake_key),
    UNIQUE (id, school_id),
    CHECK (valid_from IS NULL OR valid_until IS NULL OR valid_from <= valid_until),
    CHECK (verification_status <> 'verified' OR (reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)),
    CHECK (NOT published OR (verification_status = 'verified' AND program_scope <> 'unknown'))
);
-- Tier values have an explicit basis. Never compare a per-term value with a
-- full-degree value. Percentage/free-tuition benefits need a rate basis as well.
CREATE TABLE scholarship_tiers (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    scholarship_id BIGINT NOT NULL REFERENCES scholarships(id) ON DELETE CASCADE,
    tier_key TEXT NOT NULL,
    eligibility_text TEXT NOT NULL,
    is_renewable BOOLEAN,
    renewal_conditions TEXT,
    value_kind TEXT NOT NULL CHECK (value_kind IN ('money', 'tuition_percentage', 'tuition_waiver', 'unknown')),
    min_value NUMERIC(14,2),
    max_value NUMERIC(14,2),
    currency CHAR(3) CHECK (currency ~ '^[A-Z]{3}$'),
    payment_basis TEXT NOT NULL DEFAULT 'unknown'
        CHECK (payment_basis IN ('unknown', 'one_time', 'per_term', 'per_year', 'total_degree')),
    max_instalments INTEGER CHECK (max_instalments > 0),
    tuition_rate_basis TEXT CHECK (tuition_rate_basis IN ('domestic', 'international', 'unknown')),
    value_display_text TEXT NOT NULL,
    evidence_text TEXT NOT NULL CHECK (length(trim(evidence_text)) > 0),
    UNIQUE (scholarship_id, tier_key),
    CHECK (min_value IS NULL OR min_value >= 0),
    CHECK (max_value IS NULL OR max_value >= 0),
    CHECK (min_value IS NULL OR max_value IS NULL OR min_value <= max_value),
    CHECK (value_kind <> 'money' OR currency IS NOT NULL),
    CHECK (value_kind <> 'tuition_percentage' OR
        (min_value IS NOT NULL AND max_value IS NOT NULL AND max_value <= 100)),
    CHECK (value_kind NOT IN ('tuition_percentage', 'tuition_waiver') OR tuition_rate_basis IS NOT NULL),
    CHECK (value_kind <> 'tuition_waiver' OR (min_value IS NULL AND max_value IS NULL))
);
-- school_id is carried to enforce both endpoints belonging to the same school.
CREATE TABLE scholarship_programs (
    scholarship_id BIGINT NOT NULL,
    program_id BIGINT NOT NULL,
    school_id BIGINT NOT NULL,
    PRIMARY KEY (scholarship_id, program_id),
    FOREIGN KEY (scholarship_id, school_id) REFERENCES scholarships(id, school_id) ON DELETE CASCADE,
    FOREIGN KEY (program_id, school_id) REFERENCES programs(id, school_id) ON DELETE CASCADE
);
CREATE INDEX idx_scholarships_school_published ON scholarships(school_id) WHERE published;
CREATE INDEX idx_scholarship_programs_program ON scholarship_programs(program_id);
CREATE INDEX idx_tiers_scholarship ON scholarship_tiers(scholarship_id);

CREATE FUNCTION touch_scholarship_updated_at() RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = clock_timestamp();
    RETURN NEW;
END;
$$;
CREATE TRIGGER scholarships_updated_at BEFORE UPDATE ON scholarships
    FOR EACH ROW EXECUTE FUNCTION touch_scholarship_updated_at();
COMMIT;

-- Example query (bind :school_id / :program_id in the application):
-- SELECT s.* FROM scholarships s
-- WHERE s.school_id = :school_id AND s.published
--   AND (s.valid_from IS NULL OR s.valid_from <= CURRENT_DATE)
--   AND (s.valid_until IS NULL OR s.valid_until >= CURRENT_DATE)
--   AND EXISTS (SELECT 1 FROM programs p WHERE p.id = :program_id AND p.school_id = s.school_id)
--   AND (s.program_scope = 'school_wide'
--        OR (s.program_scope = 'selected_programs' AND EXISTS (
--            SELECT 1 FROM scholarship_programs sp
--            WHERE sp.scholarship_id = s.id AND sp.program_id = :program_id)));
-- Also filter applicant eligibility/intake/level; being visible is not proof of eligibility.
```

### 5.5. Truy vấn học bổng trên trang chi tiết ngành

Dùng `EXISTS` để không nhân bản dòng học bổng khi bảng nối có nhiều liên kết. Điều kiện trường được đặt ngoài nhánh OR; đồng thời kiểm tra ngành đang xem thuộc trường đó.

```sql
SELECT s.*
FROM scholarships s
WHERE s.school_id = :school_id
  AND s.published IS TRUE
  AND (s.valid_from IS NULL OR s.valid_from <= CURRENT_DATE)
  AND (s.valid_until IS NULL OR s.valid_until >= CURRENT_DATE)
  AND EXISTS (
      SELECT 1 FROM programs p
      WHERE p.id = :program_id AND p.school_id = s.school_id
  )
  AND (
      s.program_scope = 'school_wide'
      OR (
          s.program_scope = 'selected_programs'
          AND EXISTS (
              SELECT 1 FROM scholarship_programs sp
              WHERE sp.scholarship_id = s.id
                AND sp.program_id = :program_id
          )
      )
  );
```

Ứng dụng vẫn phải lọc intake, applicant category, bậc học và điều kiện của học sinh. Việc một học bổng được hiển thị không tự động có nghĩa học sinh đủ điều kiện nhận.

## 6. Ánh xạ kết quả crawl vào schema

### 6.1. Bảng ánh xạ

| Đầu vào từ crawler | Đích lưu trữ | Xử lý bắt buộc |
|---|---|---|
| `slug`, `school_name` | `schools` / trường hiện có | Tra cứu trường; không tạo trùng theo tên. |
| URL nguồn + `crawl_metadata` + bằng chứng HTML | `scholarships.source_url`, `source_fetched_at`, `evidence_json` | Lưu link và thời điểm lấy dữ liệu trực tiếp; HTML/hash tiếp tục nằm trong output crawl để đối chiếu. |
| Heading/hàng chứa tên award | `scholarships.name_en`, `external_key` | Tách gói thực; gộp candidate trùng; tạo định danh bền vững. |
| Nhóm intake / câu thời gian | `intake_key`, `valid_from`, `valid_until` | Không dùng thời điểm crawl thay cho intake/hiệu lực. |
| Bảng điểm và từng hàng | `scholarship_tiers` | Nối đúng header, footnote và điều kiện từng bậc. |
| `monetary_mentions`, `amount_claims` | Giá trị trong `scholarship_tiers` | Loại học phí/đặt cọc/tổng quỹ; xác định currency và payment basis trước khi ghi số. |
| Evidence gia hạn | `is_renewable`, ghi chú chung/riêng tier | Xử lý phủ định và không gộp quy tắc nhiều gói. |
| Evidence eligibility / deadline | Các trường điều kiện/hồ sơ | Giữ câu gốc; chỉ chuẩn hóa ngày khi có đủ ngày/năm/timezone cần thiết. |
| Evidence ngành | `program_scope`, `scholarship_programs` | Ánh xạ tới ngành có thật và cùng trường; chưa rõ thì giữ unknown. |
| Bằng chứng DOM/bảng | `evidence_json`, `raw_tables_json`, `evidence_text` | Giữ khả năng truy lại từng quyết định chuẩn hóa. |

### 6.2. Quy trình ingestion đề xuất

1. Đưa JSON và HTML vào vùng dữ liệu thô; kiểm tra `success`, nguồn và hash.
2. Xác định award, intake, đối tượng và tier; xử lý các candidate chồng lặp.
3. Chuẩn hóa các trường có đủ bằng chứng; giữ unknown cho phần chưa rõ và loại khỏi diện công bố.
4. Ghi offering, tier và quan hệ ngành trong transaction, dựa trên các khóa unique/FK.
5. Người duyệt đối chiếu điều khoản chính thức, ghi reviewer/thời gian và quyết định `verified` hoặc `rejected`.
6. Chỉ sau bước duyệt và kiểm tra nghiệp vụ mới bật `published`.

**Trạng thái thực hiện:** đã có crawler, output và DDL tham chiếu; chưa có ETL tự động nhập candidate vào bảng scholarship đã duyệt. Không ánh xạ trực tiếp một record trường thành một scholarship.

## 7. Giới hạn và hướng hoàn thiện

| Giới hạn quan sát được | Công việc tiếp theo |
|---|---|
| 3 nguồn không lấy được HTML trong đợt này | Lấy bản nguồn chính thức qua phương thức truy cập phù hợp, giữ provenance và đối chiếu lại; không dựng dữ liệu thay thế. |
| Candidate chưa được duyệt và có thể chồng lặp | Hoàn thiện nhận diện award/tier và bước duyệt theo bằng chứng. |
| Điều kiện nằm trong footnote hoặc trang liên kết | Bổ sung parser theo trường và thu thập terms chi tiết trước khi chuẩn hóa. |
| Một tier có thể có nhiều thành phần chi trả | Schema hiện có một payment basis/giá trị chính mỗi tier; nếu cần lưu độc lập tiền năm đầu, năm sau và tổng toàn khóa thì mở rộng bảng thành phần giá trị/lịch trả, không nhét các basis khác nhau vào cùng min/max. |
| Hạn chế quốc tịch, campus, ngoại lệ ngành chưa có bảng riêng | Hiện giữ trong eligibility/evidence; bổ sung quan hệ có cấu trúc khi có yêu cầu lọc tự động và dữ liệu đã kiểm chứng. |
| Chưa có lịch sử thay đổi đầy đủ ở cấp trường dữ liệu | URL và thời điểm lấy dữ liệu nằm trên `scholarships`; HTML/hash được lưu ngoài CSDL trong output. Muốn audit mọi lần duyệt/cập nhật cần thêm bảng lịch sử. |
| DDL tham chiếu chưa gắn với schema portal thực tế | Đối chiếu bảng trường/ngành và yêu cầu sản phẩm trước khi tạo migration tích hợp. |

## 8. Kết luận nghiên cứu

Nghiên cứu đạt mục tiêu xác định những dạng dữ liệu thực tế cần quản lý cho bài toán học bổng tại LOA Portal. Kết quả của 10 nguồn truy cập được cho thấy ít nhất ba lớp thông tin phải tách biệt: trang/bằng chứng nguồn, gói theo kỳ tuyển sinh và bậc quyền lợi theo điều kiện. Các trường hợp Humber và Lakehead chứng minh sự khác nhau giữa cấp một lần và gia hạn; uOttawa thể hiện nhiều gói có điều kiện và lịch cấp khác nhau; IBU cho thấy rủi ro lẫn chi phí với quyền lợi; Algonquin và Waterloo thể hiện phạm vi ngành và tiêu chí lựa chọn đa dạng; Regina và Lethbridge cung cấp lịch hồ sơ theo nhóm; MacEwan và Queen’s cho thấy dữ liệu có thể được trình bày bằng văn bản thay vì bảng tài chính.

Từ các kết quả đó, mô hình năm bảng được đề xuất nhằm bảo toàn nguồn, tách offering và tier, kiểm soát quan hệ ngành, duy trì trạng thái chưa xác định và chỉ cho phép công bố sau duyệt. DDL và các ràng buộc đã được kiểm tra trong môi trường PostgreSQL tạm. Phần chưa hoàn tất là thu thập ba nguồn bị chặn, duyệt danh tính từng award, hoàn thiện điều khoản và tích hợp với cơ sở dữ liệu thực tế của portal. Vì vậy, kết quả hiện tại là nền tảng nghiên cứu và thiết kế có bằng chứng, chưa phải danh mục học bổng sẵn sàng tư vấn tự động.

