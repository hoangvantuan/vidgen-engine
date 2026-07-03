# Hook & cấu trúc kể chuyện — craft giữ chân (Stage 1 · vidgen-script)

Tri thức để viết brief/kịch bản/storyboard cuốn hút. **Đã lọc qua research đối kháng** — mọi con
số retention cụ thể mà nguồn marketing hay bịa (X% giữ chân, +Y% watch-time) đã bị bác, KHÔNG dùng.
Chỉ giữ nguyên tắc có nguồn đứng vững.

## 1 · Mở đầu (hook) — nơi tụt người xem mạnh nhất

Bằng chứng (confidence trung bình→cao):
- **Short-form (9:16, TikTok/Reels/Shorts):** 3 giây đầu là cửa sổ **"lướt hay ở lại"**. Người
  xem gặp Short THỤ ĐỘNG trong feed (autoplay), quyết trong 1-2 giây. Frame mở đầu + câu nói đầu
  tiên phải giành được chú ý, nếu không đường retention tụt thẳng trong 3 giây.
- **Long-form (16:9, YouTube):** độ tụt dốc mạnh nhất nằm ở **15-30 giây đầu**. YouTube Help
  (nguồn CHÍNH THỨC) xác nhận báo cáo "Intro" đo bằng *% khán giả còn xem sau 30 giây đầu* → 30
  giây mở đầu là cửa sổ retention đo được. Dồn công sức hook vào đây.

Cách làm (điền vào khối `hook` của manifest + cảnh mở `role:"hook"`):
- **`first_frame`** — frame hình đầu tiên phải GÂY TÒ MÒ, không phải logo/dạo đầu. Đưa mô tả này
  vào `prompt` của cảnh 1 (chọn frame khung đầu đắt nhất).
- **`spoken`** — câu VO đầu tiên MẠNH NHẤT, đặt lên đầu. Không "Xin chào các bạn", vào thẳng.
- **`promise`** — mở một **open loop** (vòng chưa đóng) hoặc **curiosity gap** (khoảng tò mò):
  hứa một điều sẽ được giải đáp nếu xem tiếp. Đóng loop này ở payoff.
- **Long-form: cold-open** — cắt phần dạo đầu chậm, vào cảnh/câu hỏi/hình mạnh trước, giới thiệu
  sau. Nêu giá trị ("bạn sẽ biết được…") sớm.

Mẫu hook hay dùng (chọn theo nội dung): câu hỏi bỏ ngỏ · tuyên bố ngược đời · kết quả trước–quá
trình sau · "đừng làm X nếu chưa biết Y" · hình ảnh bất thường ở frame đầu.

> ⚠️ Không hứa con số ("giữ 85% là gấp 2.8 lần view") — các benchmark này đã bị research bác sạch.
> Chỉ nói nguyên tắc: mở đầu quyết định phần lớn việc giữ chân.

## 2 · Cấu trúc kể chuyện (điền `scenes[].role`)

Chọn 1 trong 2 khung theo bản chất nội dung:

**a. Ba hồi (three-act)** — mặc định, hợp nội dung CÓ mâu thuẫn/hành trình:
- Hồi 1 setup (giới thiệu + hook) → Hồi 2 development/confrontation (leo thang) → Hồi 3
  payoff/resolution (cao trào + kết). `role`: hook → setup → development → turn → payoff → cta.

**b. Kishōtenketsu (4 phần)** — hợp video KHÔNG dựa xung đột (giải thích, du lịch, cảm xúc, kể
chuyện đời thường, ru ngủ). Bằng chứng: đây là khung kể 4 phần cổ điển Á Đông, **không lấy xung
đột làm cột sống** (khác three-act phương Tây):
- **ki** (起 giới thiệu) → **shō** (承 phát triển, đào sâu) → **ten** (転 **bước ngoặt/đảo chiều
  bất ngờ** — trái tim của khung) → **ketsu** (結 kết, hòa giải hai mạch). `role`: hook(ki) →
  development(shō) → turn(ten) → payoff(ketsu).
- Sức hút đến từ `ten`: một liên hệ/góc nhìn bất ngờ, không cần ai thắng ai. Vẫn CÓ THỂ có căng
  thẳng, chỉ là nó không phải xương sống.

## 3 · Giữ nhịp giữa video (chống tụt ở khúc giữa)

- **Pattern interrupt** — thay đổi để "đánh thức" lại chú ý: đổi giọng điệu, đổi cỡ cảnh, chèn
  hình/góc nhìn mới, câu hỏi trực tiếp. **HONEST (research bác "mỗi 30-45s" cố định):** đặt theo
  **điểm tụt thực tế**, khoảng cách **biến thiên** — KHÔNG theo đồng hồ đều đặn. Cắt chặt ở đầu,
  nới dần sau khi đã giữ được người xem.
- **Open loop nối tầng** — trước khi đóng câu hỏi cũ, hé mở câu hỏi kế → khán giả luôn có lý do
  xem tiếp. Đây là cơ chế chống drop-off ở MỌI điểm, không chỉ hook.
- **Đa dạng cỡ cảnh & nhịp** — xem `shot_size` (mục storyboard): cảnh liền kề đổi cỡ (wide↔close)
  tạo nhịp thị giác, chống đơn điệu.

## 4 · CTA

- **1 CTA duy nhất, rõ ràng**, đặt ở payoff/cuối (reel: đúng 1 CTA). Nhiều CTA = loãng. Đặt cảnh
  cuối `role:"cta"`.

## Map vào stage / manifest

- **Đây là Stage 1 (vidgen-script).** Áp dụng khi viết `brief.md`, `kichban.md`, và điền
  `project.json`: khối `hook{}`, `scenes[].role`, và ảnh hưởng cách chia cảnh (cảnh hook đầu tư nhất).
- Checklist tự-QC gate 1 nên kiểm: có hook trong 3s/30s? có open loop? cấu trúc rõ (3 hồi hay
  kishōtenketsu)? 1 CTA?

## Nguồn (đã verify 3-0 hoặc nguồn chính thức)

- YouTube Help — Audience retention report (intro = % còn xem sau 30s): support.google.com/youtube/answer/9314415
- overseeros.com/blog/youtube-hook-framework · youtube-retention-architecture-2026
- humbleandbrag.com (3s swipe-or-stay); OpusClip 2025 (short-form drop 3s)
- Kishōtenketsu: en.wikipedia.org/wiki/Kishōtenketsu (+ Art of Narrative, Mythic Scribes)
- ĐÃ BÁC (không dùng): mọi benchmark %/độ dài của retentionrabbit, tubeai, ttsvibes; "pattern
  interrupt mỗi 30-45s".
