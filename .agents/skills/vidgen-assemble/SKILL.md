---
name: vidgen-assemble
description: STAGE 4 của pipeline vidgen — RÁP video hoàn chỉnh: TTS ElevenLabs khớp timestamp → phụ đề .ass → clip từng cảnh setpts khớp lời đọc → nhạc nền ducking → end-card → final.mp4. Dùng khi cần "ráp video", "ghép các clip lại", "thêm giọng đọc và phụ đề", "xuất video cuối", "dựng bản final", hoặc khi vidgen-flow gọi STEP 4. Reel brand Akasto → dùng akasto-reel-builder thay skill này.
---

# Vidgen Assemble (clip + giọng + sub + nhạc → final.mp4)

Nguyên lý khớp nhịp: TTS trả timestamp từng chữ → biết chính xác lời cảnh nào bắt đầu/kết thúc
lúc nào → mỗi clip đổi tốc độ (`setpts`, KHÔNG loop nên không giật) khớp đúng khoảng lời của nó.
Vì vậy **TTS chạy TRƯỚC, video khớp theo giọng** — không phải ngược lại.

```bash
PY=~/.venv/claude/bin/python
SK=.agents/skills/vidgen-assemble/scripts
```

## Bước 1 · Giọng đọc + phụ đề + timings

Cần `ELEVENLABS_API_KEY` (thiếu → skill setup-api-key). Chọn voice cùng user trước.
```bash
$PY $SK/tts_to_ass.py --project projects/<tên> --voice <VOICE_ID>
```
Đọc VO mọi cảnh từ manifest → xuất `05_audio/narration.mp3` + `subs.ass` (khớp giọng,
font Be Vietnam Pro, nằm trong safe-zone 9:16) + `timings.json` (khoảng thời gian từng cảnh).
Video không lời đọc → bỏ bước này, khi ráp mỗi cảnh giữ đúng `duration`.
Nghe thử narration trước khi ráp — giọng đọc sai thì sửa VO/đổi voice ngay, đừng để tới final.

## Bước 2 · Ráp

```bash
$PY $SK/assemble.py --project projects/<tên> --bgm nhac.mp3 --endcard cta.png
```
Làm gì: mỗi clip cover-crop đúng khung (Flow trả 720×1280, tự scale lên) + bỏ audio gốc Veo
+ retime khớp `timings.json` (clip DÀI hơn đích → cắt giữ tốc độ thật; NGẮN hơn → làm chậm
mượt bằng setpts — không freeze, không giật) → nối → burn sub → nhạc nền ducking theo giọng
(sidechaincompress) → end-card nán cuối chống cụt → `06_final/final.mp4` (30fps, H.264, faststart).
Cảnh nào clip `failed` nhưng có ảnh đã gen → tự **fallback Ken Burns** (zoompan ảnh tĩnh)
để video không thủng lỗ — Flow từ chối gen một số nội dung, đừng để 1 cảnh chặn cả video.
**Transition per-cut theo cảm xúc:** đặt `scenes[].transition` trong manifest (dissolve vào mơ,
fadewhite tỉnh giấc, fade dịu, cut nhịp nhanh) hoặc `--xfade "fade:0.5"` áp mọi cắt cảnh.
Script tự render mỗi cảnh DƯ đúng phần xfade "ăn" nên video vẫn khớp narration.
Tùy chọn: `--no-burn` xuất KIT (base sạch + sub rời) giao CapCut · `--tail` chỉnh giây nán ·
`--fonts-dir` nếu máy thiếu font tiếng Việt.

## Bước 3 · GATE 3 (final review)

Trình user bản final + tự-QC: ☐ sub khớp giọng, không tràn safe-zone ☐ chuyển cảnh khớp lời
☐ nhạc không đè giọng ☐ không cụt đuôi ☐ đúng aspect/nền tảng đích.
User gật → set `gates.final_approved = true`. Chê chỗ nào sửa đúng chỗ đó:
- Sai lời/giọng → sửa VO trong manifest → chạy lại từ Bước 1 (clip giữ nguyên).
- Clip xấu → quay lại vidgen-clips gen đúng cảnh đó → chỉ chạy lại Bước 2.
- Chỉnh nhạc/end-card → chạy lại Bước 2 (nhanh, không tốn gì).

## Sự cố hay gặp

**Giới hạn QC của AI (bắt buộc nhớ):** AI soi được HÌNH (frame, bố cục, sub) nhưng KHÔNG
nghe audio, KHÔNG xem chuyển động — độ mượt chuyển cảnh + chất lượng giọng đọc bắt buộc
human nghe/xem thật ở GATE 3, đừng tự kết luận "mượt rồi".

| Hiện tượng | Xử lý |
|---|---|
| ffmpeg báo thiếu libass / không burn sub | Bản brew rút gọn — script tự xuất sub rời cạnh final; muốn burn: cài ffmpeg có `--enable-libass` |
| Sub ô vuông/mất dấu | Thiếu font — trỏ `--fonts-dir` tới thư mục chứa Be Vietnam Pro |
| Clip bị kéo chậm/nhanh bất thường | VO cảnh đó dài/ngắn hơn duration nhiều — cân lại VO hoặc duration rồi gen lại cảnh |
| ffmpeg lỗi | Xem lệnh in ra; kiểm clip nguồn có cảnh nào 0 byte (gen failed) không |
