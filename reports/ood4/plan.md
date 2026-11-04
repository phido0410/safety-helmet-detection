# OOD-4: kế hoạch đánh giá độc lập bản triển khai (chốt 2026-11-03, trước khi thu thập ảnh)

## Vì sao cần

OOD-1/2/3 đã ảnh hưởng tới thiết kế: OOD-1 dùng để tìm lỗi của M2, kết quả ngoài miền dẫn tới M3 và M3b, và bảng độ chính
xác theo chiều cao người trên OOD-1/2/3 được xem trước khi quyết định làm ngưỡng chiều cao tối thiểu. Bản triển khai cuối
(M3b + quy tắc bộ phận – toàn thể τ = 0,05 + ngưỡng vi phạm 0,169 + chiều cao tối thiểu 160 px) vì vậy cần một tập chưa ai xem.

## Thu thập

- Ảnh trong bài báo Việt Nam về công trường, **khác mọi danh sách trước** (reports/ood, ood2, ood2b, ood3, ood3b); bỏ laodong.vn
  (chặn truy cập tự động). Danh sách ở `reports/ood4/news_articles.txt`, tìm ngày 2026-11-03.
- `scripts/collect_ood.py --name ood4 --news-only --exclude` ảnh và ảnh bị bỏ của mọi tập trước (bỏ ảnh gần trùng).
- Mục tiêu khoảng 100 ảnh gán nhãn được; thiếu thì thêm một đợt (`ood4b`) với cùng quy tắc, **trước** khi đánh giá.
- Ảnh thuộc bản quyền tòa soạn: chỉ dùng nội bộ để đánh giá, không commit, không đưa vào huấn luyện.

## Gán nhãn

- Như OOD-3 (`scripts/label_ood.py`, quy tắc ở docstring): YOLO26l COCO chỉ đề xuất khung người, Claude (AI) duyệt từng ảnh và
  quyết định đội mũ bảo hộ hay không. Gán mọi người trong khu thi công thấy được đầu và phán đoán được (kể cả nhỏ, tối, ở mép, chỉ
  thấy đầu); không gán người đi đường / xe máy ngoài khu thi công; mũ vải, mũ lưỡi trai, nón lá = không đội; mũ bảo hiểm xe máy =
  có đội. Ảnh cảnh rộng soát toàn ảnh, không chỉ trong khung đề xuất.
- Sinh viên kiểm tra phiếu (`label_ood.py check`: 20 ảnh ngẫu nhiên seed 42 + mọi ảnh có hộp ghi "không chắc") trước khi đánh giá.
- Báo cáo ghi rõ nhãn do AI gán.

## Đánh giá (một lần, sau khi nhãn đã chốt)

1. Mô hình M3b như OOD-1/2/3 (`scripts/eval_ood.py`): mAP@0.5 hai lớp người, chênh so với test SHEL5K (0,905; mục tiêu ≤ 0,15),
   Recall / Precision lớp vi phạm ở ngưỡng 0,213, bảng theo chiều cao người và theo loại mũ.
2. Bản triển khai (`scripts/eval_min_size.py`, áp H = 160 px đã chọn trên val, không chọn lại): Recall / Precision vi phạm khi
   tính mọi người và khi chỉ tính người ≥ 160 px, tỉ lệ người vi phạm bị bỏ qua vì nhỏ hơn 160 px.

**Không thay đổi mô hình, ngưỡng hay quy tắc nào sau khi xem kết quả OOD-4.** Kết quả được báo cáo nguyên trạng, kể cả khi
không đạt mục tiêu.

## Bổ sung trước khi gán nhãn (2026-11-04)

`collect_ood.py` thu được 200 ảnh. Lọc nhanh bằng ảnh ghép (loại flycam, hội trường / phòng họp, phố xá, ảnh không có người gán
được): còn 156 ảnh (144 giữ + 12 cần xem kỹ). Lấy ngẫu nhiên 110 ảnh (seed 42) trong 156 ảnh này để gán nhãn, đủ khoảng 100 ảnh
sau khi bỏ thêm ảnh không gán được. 90 ảnh còn lại không gán nhãn, không đánh giá (chuyển vào `data/ood4/unused`). Việc chọn làm
trước khi gán nhãn và trước khi chạy bất kỳ đánh giá nào trên OOD-4.

## Gán nhãn xong (2026-11-04, trước khi chạy bất kỳ đánh giá nào trên OOD-4)

110 ảnh được duyệt (Claude, theo quy tắc trên): 105 ảnh gán nhãn, 5 ảnh bỏ (3 ảnh đám đông chen nhau không khoanh được từng
người, 1 ảnh chỉ thấy lưng người trên cột điện, 1 ảnh chỉ còn người dân / người đi đường); person_with_helmet 210 hộp,
person_no_helmet 146 hộp. Tự soát 13 hộp thêm / sửa tay bằng ảnh cắt: bỏ 4 hộp (2 hộp tọa độ ước lượng sai chỗ, 2 hộp không
phán đoán được đầu). Phiếu kiểm tra cho sinh viên: 32 ảnh có hộp "không chắc" + 20 ảnh ngẫu nhiên (seed 42),
`data/ood4/review/check_*.jpg`.
