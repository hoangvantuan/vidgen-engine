# Phụ đề động, âm thanh & chuyển cảnh (Stage 4 · vidgen-assemble)

Craft cho hậu kỳ. **Cảnh báo trung thực (chánh kiến):** research đã **bác sạch mọi số liệu** kiểu
"phụ đề tăng retention X%" (Facebook +12%, Verizon 92% tắt tiếng, Discovery +7,32%). Vì vậy phụ đề
karaoke ở đây là **quy ước dễ đọc trên mạng xã hội** (nhiều người xem không bật tiếng), KHÔNG phải
"đòn bẩy retention có bằng chứng". Kỹ thuật thì thật; con số thì đừng hứa.

## 1 · Phụ đề karaoke (word-level highlight) — quy ước styling

Cơ chế (nguồn craft): tô sáng chạy theo từng CHỮ bằng tag ASS **`\kf`** (fill mượt từ màu phụ →
màu chính theo thời lượng chữ), tạo hiệu ứng "sweep" đặc trưng.
- **Màu:** chính (đang đọc) = **vàng / cyan / màu brand**; phụ (chưa đọc) = **trắng / xám nhạt**;
  **viền đen 3-4px**. Tương phản phải đủ: trắng→vàng OK; trắng→xám nhạt KHÔNG đủ tương phản.
- **Mật độ:** tối đa **4-6 chữ hiển thị cùng lúc** (sweep không chạy quá nhanh). Chèn khoảng
  **50-100ms** giữa các chữ để tránh nhấp nháy mỏi mắt.
- **Burn-in:** phụ đề social nên burn thẳng vào video (ffmpeg). Render đủ fps để màu chuyển mượt.
- **Vị trí (9:16):** nằm trong **safe-zone** — không dính mép trên/dưới (tránh bị UI TikTok/Reels
  che). Mặc định pipeline: `marginv` ~700 cho dọc.

Cần word-level timing: **ElevenLabs `convert_with_timestamps` trả timestamp TỪNG CHỮ** — đã có sẵn
trong `tts_to_ass.py` (`alignment.characters` + `character_start/end_times`), chỉ cần dựng `\kf`.

## 2 · Ducking nhạc nền dưới giọng (sidechain) — tham số chuẩn

Từ chuẩn mixing (thay cho tham số cũ hơi mạnh tay ratio 8/attack 5):
- **ratio 4:1** (rõ mà không bóp chết) · **attack 10-20ms** · **release 200-400ms** (mượt giữa câu).
- **Độ ducking:** giảm **6-10 dB** khi có giọng; nhạc nền nằm khoảng **-12 đến -18 dB** so với gốc.
- Tinh chỉnh: hồi phục gấp → tăng release 300-500ms; ducking quá gắt → hạ ratio 3:1; nhạc bị ducking
  cả lúc im → nâng threshold.
- Nguyên tắc: **giọng nổi rõ trên hết, nhạc nghe được nhưng phụ thuộc** dưới giọng.
- **Nguồn nhạc:** thư viện `assets/bgm/<mood>/` (assemble auto-pick theo `music.mood`), hoặc **gen
  bằng skill `music`** (ElevenLabs Music — composition plan nhiều đoạn theo cung cảm xúc, hợp kể chuyện).

## 3 · Giọng đọc (VO)

- Câu ngắn, chủ động, đọc to nghe tự nhiên. **Cấm em-dash `—`** trong VO tiếng Việt (AI đọc vấp).
- Nghe thử `narration.mp3` TRƯỚC khi ráp — sai giọng thì sửa VO/đổi voice ngay, đừng để tới final.
- AI **không nghe được audio** → chất lượng giọng bắt buộc human nghe ở gate 3.

## 4 · Chuyển cảnh theo cảm xúc (điền `scenes[].transition`)

Đặt transition SAU mỗi cảnh theo mạch cảm xúc, KHÔNG đồng loạt 1 kiểu (nguồn: StudioBinder):
- **cut** (cắt cứng) — nhịp nhanh, năng lượng, tương phản mạnh. (bỏ field = cut)
- **fade** (cross-dissolve) — trôi thời gian, đoạn dịu, suy tư. dur 0.4-0.6s.
- **dissolve** — vào mơ/hồi tưởng.
- **fadewhite** — tỉnh giấc, nhảy thời gian, thăng hoa.
- **match cut** — nối 2 cảnh qua yếu tố hình/âm giống nhau (liên tục chủ đề) — dựng ở tầng kịch bản.
- **J-cut** (tiếng cảnh sau vào TRƯỚC hình) — tạo mong đợi, dẫn dắt; **L-cut** (tiếng cảnh trước
  kéo SANG hình cảnh sau) — giữ mạch, làm mượt đổi bối cảnh. Hai loại này làm ở tầng AUDIO khi ráp
  (giọng/âm dẫn hoặc trễ so với cắt hình), không phải xfade hình.

## Map vào stage

- **Ráp-hậu kỳ (Stage 4):** karaoke sub + ducking + transition thực thi trong `tts_to_ass.py` /
  `assemble.py`. `music.mood` → auto-pick nhạc.
- Checklist gate 3: sub karaoke khớp giọng, trong safe-zone, 4-6 chữ? nhạc ducking không đè giọng?
  chuyển cảnh khớp cảm xúc? không cụt đuôi?

## Nguồn

- vidno.ai/blog/karaoke-style-word-highlight-captions (\\kf, màu, 4-6 chữ, 50-100ms)
- store.hollyland.com (ducking: ratio 4:1, attack 10-20ms, release 200-400ms, 6-10 dB)
- studiobinder.com/blog/types-of-editing-transitions-in-film (J/L cut, match cut)
- ĐÃ BÁC (không dùng): mọi số liệu "phụ đề tăng retention %" (3playmedia và phái sinh).
