# Hướng dẫn gán nhãn tập ngoài miền (OOD-1 → OOD-4)

Bản 2026-11-04. Gộp các lần sinh viên kiểm tra phiếu gán nhãn (OOD-1 tuần 9, OOD-2b, OOD-3, OOD-3b, OOD-4) thành một bộ quy
tắc. Ở tuần 9, quy tắc 6 được áp lại cho các tập trước bằng cách rà lại mọi khung đề xuất bị bỏ (quy tắc 2 và 7 thì
không rà lại riêng); sau lần kiểm tra OOD-4, cả bốn tập được rà lại theo hai quy tắc mới (8, 10) rồi mới đánh giá lại. Nhãn do Claude (AI) gán, YOLO26l COCO chỉ đề xuất khung
người, sinh viên kiểm tra phiếu ngẫu nhiên + các hộp ghi "không chắc". Công cụ: `scripts/label_ood.py`.

## Lớp

Chỉ 2 lớp người: `person_with_helmet` (pwh), `person_no_helmet` (pnh). Không gán helmet, head, face.

1. **Mũ bảo hộ** (mũ nhựa cứng của công trường, kể cả loại gắn vành / vải che nắng) = có đội.
2. **Mũ bảo hiểm xe máy** = có đội (sinh viên chốt 2026-11-02).
3. **Mọi loại mũ khác** (mũ vải, mũ lưỡi trai, nón lá, mũ cối, mũ trùm áo, khăn trùm) và đầu trần = không đội. Ghi loại mũ vào
   cột `headwear` (đầu trần, nón lá, mũ vải, mũ lưỡi trai, mũ cối, mũ khác, không rõ).

## Gán ai

4. **Gán mọi người có mặt trong cảnh công trường** mà phán đoán được đầu: thợ, kỹ sư, cán bộ đến công trường, người đứng xem
   trong khu thi công, kể cả người cởi trần, người lái máy thấy rõ đầu.
5. **Không gán người ngoài khu thi công**: người đi đường, đi xe máy trên phố cạnh công trường, người dân sau hàng rào.
6. **Gán cả người nhỏ, tối, ở mép ảnh, mờ do lấy nét** nếu vẫn phán đoán được đầu. Người bị mép ảnh cắt nhưng thấy rõ đầu vẫn
   gán. Không thấy đầu (chỉ thấy chân, tay, lưng) hoặc đầu quá nhỏ để phán đoán thì không gán.
7. **Ảnh cảnh rộng phải soát toàn ảnh**, không chỉ trong khung YOLO đề xuất (người trên giàn giáo, ban công, mái hay bị sót).

## Hộp

8. **Mỗi người đúng một hộp.** Không vẽ thêm hộp cho một phần cơ thể của người đã có hộp (đầu, áo, nửa trên), không giữ hai
   hộp trùng nhau; khung đề xuất gộp hai người thì sửa lại thành hộp của từng người.
9. Hộp bao phần thân nhìn thấy được.
10. **Người bị người khác hoặc vật (cột, tường, máy, cabin, thành xe) che quá 40% cơ thể thì không gán** mà ghi là
    **vùng bỏ qua** (`ignore`): khi đánh giá, dự đoán trùng vùng này không tính đúng cũng không tính sai (như CityPersons,
    CrowdHuman). Quy tắc này không áp cho người bị mép ảnh cắt (xem 6).
11. Ảnh đám đông chen nhau đến mức không khoanh được từng người thì bỏ cả ảnh.

## Ảnh

12. Bỏ ảnh không phải cảnh công trường (hội trường, phòng họp, phố xá, flycam người quá nhỏ, ảnh đồ họa) hoặc không còn người
    nào gán được.

## Kiểm tra

13. Hộp thêm tay phải soát lại bằng ảnh cắt phóng to trước khi đưa sinh viên kiểm tra (tọa độ ước lượng dễ lệch).
14. Phiếu kiểm tra: mọi ảnh có hộp ghi "không chắc" + 20 ảnh ngẫu nhiên (seed 42). Sinh viên sửa thì ghi "(anh kiểm tra: …)"
    vào ghi chú; quy tắc mới rút ra từ lần kiểm tra được thêm vào tài liệu này và rà lại mọi tập.

## Lịch sử quy tắc

- OOD-1 (tuần 9): quy tắc gốc (đầu cao ≥ 12 px, mũ không phải mũ bảo hộ = không đội).
- 2026-11-02 (kiểm tra OOD-3): gán cả người nhỏ, tối, ở mép nếu thấy đầu (6); soát toàn ảnh (7); không gán người đi đường (5).
- 2026-11-02 (kiểm tra OOD-2b): mũ bảo hiểm xe máy = có đội (2).
- 2026-11-04 (kiểm tra OOD-4): mỗi người một hộp (8); che > 40% thì không gán, dùng vùng bỏ qua (10); người cởi trần đứng trong
  cảnh công trường phải gán (4).
