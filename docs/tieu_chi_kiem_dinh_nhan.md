# Tiêu chí kiểm định chất lượng nhãn SHEL5K (Tuần 2)

Mục đích: ước lượng tỉ lệ nhãn sai, nhãn thiếu, nhãn trùng của SHEL5K bằng cách lấy mẫu ngẫu nhiên 300 ảnh
(seed cố định = 42). Kết quả chỉ để đo lường; việc sửa/loại nhãn thuộc Tuần 4.

Tiêu chí được chốt **trước khi** xem ảnh và áp dụng thống nhất cho cả 300 ảnh.

## Sáu lớp cần kiểm tra

| ID | Lớp | Hộp bao gì | Ghi chú |
|---|---|---|---|
| 0 | `helmet` | Chỉ riêng chiếc mũ bảo hộ | Nhỏ hơn và nằm trong `head_with_helmet` |
| 1 | `head` | Đầu **không** đội mũ bảo hộ | Mọi loại mũ không phải mũ bảo hộ (mũ vải, mũ lưỡi trai, nón…) đều tính là không đội mũ bảo hộ |
| 2 | `head_with_helmet` | Đầu **có** đội mũ, gồm cả mũ | |
| 3 | `person_with_helmet` | Toàn bộ phần nhìn thấy của người **có** đội mũ | |
| 4 | `person_no_helmet` | Toàn bộ phần nhìn thấy của người **không** đội mũ | **Lớp vi phạm, ưu tiên kiểm tra kỹ nhất** |
| 5 | `face` | Khuôn mặt nhìn thấy được | Người quay lưng thì không có |

Một người đội mũ, quay mặt về camera thường có đủ 4 hộp lồng nhau:
`person_with_helmet` ⊃ `head_with_helmet` ⊃ `helmet`, cùng `face`. Người không đội mũ có 3 hộp:
`person_no_helmet` ⊃ `head`, cùng `face`.

Những chỗ hay sai nhất, cần ưu tiên soi:

- Trạng thái mũ của hộp `person_*` không khớp với hộp đầu của cùng người (vd. `person_no_helmet` nhưng đầu là `head_with_helmet`).
- `head` và `head_with_helmet` bị nhầm khi mũ nhỏ, tối hoặc bị che.
- Người ở rìa ảnh, bị che một phần hoặc đứng xa không có hộp `person_*`.

## Đơn vị đếm

Mọi lỗi được đếm **theo hộp**. Ví dụ một người đội mũ, quay mặt về camera, hoàn toàn không có nhãn
được tính là 4 hộp thiếu (person_with_helmet, head_with_helmet, helmet, face).

## Các loại lỗi

| Loại lỗi | Định nghĩa | Ví dụ |
|---|---|---|
| **Sai lớp** | Hộp đúng vị trí một đối tượng nhưng gán sai lớp | Người đội mũ bị gán `person_no_helmet`; `head` trong khi đầu có mũ; mũ đặt trên bàn bị gán `head_with_helmet` |
| **Thiếu nhãn** | Đối tượng thuộc 1 trong 6 lớp, nhìn thấy rõ, nhưng không có hộp | Người ở rìa ảnh không có hộp `person_*`; người có hộp `person_*` nhưng thiếu hộp `helmet` |
| **Trùng nhãn** | Từ 2 hộp cùng lớp trở lên cho cùng một đối tượng | Hai hộp `helmet` gần như trùng nhau trên cùng một mũ |
| **Hộp không khít** | Hộp đúng đối tượng, đúng lớp, nhưng lệch rõ rệt: có cạnh lệch hơn khoảng 20% kích thước hộp, hoặc cắt mất một phần lớn đối tượng | Hộp `person` chỉ bao nửa người dù cả người đều nhìn thấy |
| **Hộp thừa** | Hộp không ứng với đối tượng nào | Hộp `face` trên nền trống |

## Ngưỡng "nhìn thấy rõ" (để tính thiếu nhãn)

- Phần nhìn thấy của đối tượng từ khoảng **50%** trở lên, **và**
- cạnh ngắn của đối tượng từ khoảng **8 pixel** trở lên trên ảnh gốc 416×416.
- Đối tượng dưới ngưỡng này không có nhãn thì **không** tính là thiếu.
- `face`: chỉ tính khi nhìn thấy được phần lớn khuôn mặt (không tính người quay lưng).

## Trường hợp đặc biệt

- **Vùng phản chiếu dạng gương ở mép ảnh**: đánh dấu ảnh có vùng này. Đối tượng **trong vùng phản chiếu**
  không có nhãn được đếm **riêng** (cột `mirror_unlabeled`), **không** cộng vào "thiếu nhãn".
  Nhờ vậy báo cáo có thể trình bày cả hai cách tính.
- Ngược lại, đối tượng **trong vùng phản chiếu có nhãn** thì **không** tính là hộp thừa, nhưng đếm riêng
  (cột `mirror_labeled`), vì mô hình sẽ học cả những đối tượng phản chiếu này.
- **Mũ không phải mũ bảo hộ** (quy ước đã chốt, chưa kiểm chứng trên SHEL5K): nếu dữ liệu gán người đội mũ vải,
  mũ lưỡi trai, nón… là `head_with_helmet` / `helmet` / `person_with_helmet` thì tính là **Sai lớp** và ghi chú
  `mũ khác`. Nhờ ghi chú này, kết quả kiểm định cho biết SHEL5K có theo cùng quy ước hay không.
- **Không chắc chắn** (ảnh mờ, tối, không rõ có đội mũ không): không tính lỗi, ghi vào cột ghi chú.
- **YOLO gợi ý** (khung nét đứt): chỉ là gợi ý. Mỗi gợi ý được xác nhận là *đúng thiếu nhãn* / *không phải lỗi*
  / *nằm trong vùng phản chiếu*. Số hộp thiếu được xác nhận vẫn phải cộng vào cột "thiếu nhãn" (hoặc `mirror_unlabeled`).
- Gợi ý YOLO **chồng một phần lên hộp người đã có** (IoU lớn nhất từ 0 đến 0,5) thường là người **đã có nhãn** nhưng
  hộp YOLO bao khác phạm vi: chọn *không phải lỗi*. Nếu hộp nhãn gốc thực sự lệch quá tiêu chí thì cộng vào "Hộp không khít".

## Chỉ số tổng hợp

- **Tỉ lệ ảnh có lỗi**: số ảnh có ít nhất 1 lỗi / 300, kèm khoảng tin cậy 95% (Wilson).
- **Tỉ lệ lỗi theo hộp**:
  - sai lớp, trùng, không khít, thừa: số hộp lỗi / tổng số hộp trong mẫu;
  - thiếu nhãn: số hộp thiếu / (tổng số hộp trong mẫu + số hộp thiếu).
- **Độ chính xác của YOLO gợi ý**: số gợi ý được xác nhận là lỗi thật / tổng số gợi ý.

## Kiểm tra riêng (không nằm trong mẫu ngẫu nhiên)

Các ảnh có nhãn trùng (IoU > 0,7 cùng lớp) hoặc mâu thuẫn (`head` và `head_with_helmet` gần như trùng vị trí),
nằm ngoài mẫu ngẫu nhiên, được xem riêng (20 ảnh với seed 42). Nếu trộn vào 300 ảnh
ngẫu nhiên, tỉ lệ lỗi ước lượng sẽ bị thổi phồng.
