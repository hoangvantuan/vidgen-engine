# Decision Grilling — phỏng vấn quyết định trước khi đốt credit

**Dùng chung** cho mọi điểm "hỏi user / chốt quyết định" trong bộ vidgen (brief ở
vidgen-script, chọn voice ở vidgen-assemble, phản biện 3 GATE ở vidgen-flow). Nguồn tư
tưởng: skill `grilling`. Đây là **phương pháp**, không có số liệu cần verify — đừng bịa
benchmark, đừng hứa retention.

## Vì sao grill ở đây (không phải hỏi cho có)

Triết lý gate của vidgen: **chữ rẻ → ảnh miễn phí → video tốn credit → ráp tốn công**. Một
quyết định brief sai (sai persona, sai tỉ lệ, sai mục tiêu) không lộ ở tầng chữ — nó lộ ở
tầng video khi đã đốt credit. Phỏng vấn kỹ ở tầng RẺ NHẤT chính là điểm leverage. Grill
không phải để làm khó user; grill để **moi giả định ngầm ra ánh sáng trước khi nó thành clip hỏng**.

## 5 nguyên tắc lõi (từ grilling)

1. **Hỏi TỪNG CÂU MỘT.** Bắn nhiều câu một lúc gây rối, user trả lời qua loa. Một câu →
   chờ trả lời → câu tiếp phụ thuộc câu vừa rồi.
2. **Mỗi câu KÈM đề xuất.** Không hỏi trống ("bạn muốn tỉ lệ nào?"). Hỏi kèm khuyến nghị
   + lý do ("9:16 vì đích là TikTok — đồng ý không, hay bạn cần cả bản 16:9?"). User chỉ
   cần gật/sửa, nhanh hơn nhiều.
3. **Đi theo CÂY quyết định, giải dependency trước-sau.** Quyết định gốc chốt trước vì nó
   ràng buộc các quyết định con. Chốt mục tiêu → mới bàn loại video → mới bàn thời lượng.
4. **Tự KHÁM PHÁ thay vì hỏi.** Câu nào trả lời được bằng đọc `project.json` cũ, brief đã
   có, references, hoặc suy từ điều user vừa kể → tự chốt, **báo là đã suy ra**, đừng hỏi lại.
5. **Đảo ngược mỗi quyết định.** Trước khi chốt, thầm hỏi "chọn cái này thì hỏng kiểu gì?"
   Nêu 1 failure mode cho user thấy tradeoff (âm dương). Không nêu được = chưa hiểu đủ.

## Adaptive — grill sâu chỗ mơ hồ, KHÔNG hỏi chỗ đã rõ

- User đã nói rõ / dự án cũ đã có → **im, chốt luôn**, chỉ xác nhận 1 dòng ("đích TikTok →
  9:16, mình dùng vậy nhé").
- Chỉ bung phỏng vấn ở nhánh **mơ hồ HOẶC rủi ro cao** (chọn sai thì đắt): mục tiêu lẫn
  lộn, persona chung chung, thời lượng vô lý so với loại video.
- Dừng grill khi **đã đủ để hành động không hối tiếc** — không phỏng vấn cho đủ bộ.

## Cây quyết định BRIEF (vidgen-script Bước 1) — thứ tự dependency

Chốt theo đúng thứ tự này; câu sau kế thừa câu trước:

1. **Mục tiêu DUY NHẤT** (gốc — ràng buộc tất cả). "Xem xong bạn muốn người ta LÀM một
   việc gì?" Ép về **một** việc. Nhiều mục tiêu = chưa có mục tiêu → grill tiếp tới khi còn một.
   *Đảo ngược:* video ôm 3 thông điệp → loãng, không ai nhớ gì.
2. **Persona người xem** (cụ thể, không "mọi người"). Ai? Đang ở đâu/tâm trạng gì khi xem?
   Suy được từ mục tiêu thì tự đề xuất rồi xác nhận. *Đảo ngược:* persona mờ → hook sai đối tượng.
3. **Loại video** (dẫn xuất từ mục tiêu + persona). Đề xuất 1-2 preset kèm lý do (bảng ở
   SKILL.md), đừng bắt user tự chọn. *Đảo ngược:* chọn `reel` cho nội dung cần dựng mạch dài → cụt ý.
4. **Nền tảng đích → tỉ lệ** (thường suy được từ loại video/persona). TikTok/Reels/Shorts →
   9:16; YouTube ngang → 16:9. Đề xuất rồi hỏi có cần bản repurpose không. Không hỏi trống tỉ lệ.
5. **Thời lượng đích** (ràng buộc bởi loại video + nền tảng). Đề xuất khoảng theo preset;
   kiểm chéo với số cảnh ≈ credit. *Đảo ngược:* thời lượng dài mà mục tiêu là hook nhanh → tụt reach.

Xong 5 nhánh mới sang **hook** và storyboard. Nhánh nào user đã chốt trong yêu cầu ban đầu →
bỏ qua, chỉ liệt kê lại 1 dòng "mình hiểu là …" để user kịp bắt lỗi.

## Cây quyết định CHỌN VOICE (vidgen-assemble Bước 1)

Đừng liệt kê 100 voice bắt user tự mò. Suy từ persona + mood đã chốt ở brief, đề xuất
**2-3 voice ứng viên** kèm lý do, rồi grill các trục còn mơ hồ — từng câu:

1. **Giới tính + độ tuổi giọng** — suy từ nhân vật/persona nếu có; nếu không, đề xuất theo mood.
2. **Tông cảm xúc** (ấm/trầm/tươi/kể chuyện) — khớp `music.mood` và cung năng lượng của video.
3. **Tốc độ + năng lượng** — ru ngủ → chậm, đều; reel bán hàng → nhanh, dứt khoát.
4. **Ngôn ngữ/giọng vùng** nếu có yêu cầu.

Chốt xong → nghe thử `narration.mp3` TRƯỚC khi ráp (giọng sai sửa ở đây rẻ, đừng để tới final).

## Phản biện GATE — biến "gật đầu" thành đối kháng

Gate không phải điểm xin chữ ký. Trước khi trình user, **tự phản biện như một người
hoài nghi** (nguyên lý đảo ngược): "output này SAI kiểu gì mà mình đang bỏ qua?" Chạy
checklist tự-QC của từng gate ở góc nhìn *tìm lỗi*, không phải *xác nhận đúng*. Khi trình
user, nêu **1-2 rủi ro còn lại mình chưa chắc** kèm hỏi thẳng, thay vì "ổn rồi, duyệt nhé":

- GATE 1 (script): "Hook này thật sự dừng ngón tay ở giây 3 chứ? Nếu người xem là <persona>
  mà mở bằng <first_frame>, họ lướt tiếp không?"
- GATE 2 (character): "Frame nào của clip thử nhân vật LỆCH anchor nhất — chấp nhận được không?"
- GATE 3 (final): AI **không nghe audio, không xem chuyển động** → hỏi thẳng user 2 điều đó
  ("nhạc có đè giọng chỗ nào không? chuyển cảnh 4→5 có giật không?"), đừng tự kết luận "mượt rồi".

Nguyên tắc chung mọi gate: **nêu điểm yếu trước, xin duyệt sau.** User duyệt một thứ đã bị
mình soi kỹ đáng tin hơn nhiều so với một thứ được khen sẵn.
