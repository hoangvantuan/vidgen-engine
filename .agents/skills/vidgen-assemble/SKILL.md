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

Cần `ELEVENLABS_API_KEY` (thiếu → skill setup-api-key). **Chọn voice bằng phỏng vấn, đừng
đổ 100 voice bắt user tự mò** (xem cây quyết định voice trong
`../vidgen-script/references/decision-grilling.md`): suy từ persona + `music.mood` đã chốt ở
brief → đề xuất **2-3 voice ứng viên kèm lý do** → grill các trục còn mơ hồ (giới tính/tuổi
giọng · tông cảm xúc · tốc độ/năng lượng · giọng vùng) **từng câu một**, mỗi câu kèm khuyến
nghị. Liệt kê voice:
```bash
curl -s -H "xi-api-key: $ELEVENLABS_API_KEY" https://api.elevenlabs.io/v2/voices \
  | $PY -c "import sys,json; [print(v['voice_id'], v['name']) for v in json.load(sys.stdin).get('voices',[])]"
$PY $SK/tts_to_ass.py --project projects/<tên> --voice <VOICE_ID>
```
Đọc VO mọi cảnh từ manifest → xuất `05_audio/narration.mp3` + `subs.ass` + `timings.json`.
**Phụ đề mặc định KARAOKE word-level** (tô sáng chạy theo từng chữ, dùng timestamp ElevenLabs sẵn
có), font Be Vietnam Pro, safe-zone 9:16. Tùy chọn: `--plain` (sub tĩnh), `--highlight cyan|yellow`,
`--max-words 5`. Quy ước styling + lý do — LƯU Ý karaoke là quy ước DỄ ĐỌC, KHÔNG hứa số retention
(số liệu phụ đề→retention đã bị research bác): `references/caption-and-audio.md`.
Video không lời đọc → bỏ bước này, khi ráp mỗi cảnh giữ đúng `duration`.
Nghe thử narration trước khi ráp — giọng đọc sai thì sửa VO/đổi voice ngay, đừng để tới final.

## Bước 2 · Ráp

```bash
$PY $SK/assemble.py --project projects/<tên> --endcard cta.png   # nhạc tự chọn theo music.mood
```
**Nhạc nền** (ưu tiên): `--bgm file` > `music.file` manifest > auto-pick theo `music.mood` từ
`assets/bgm/` (đổi thư mục bằng `--bgm-dir`; thả nhạc theo README ở đó). Ducking dịu (ratio 3:1,
threshold 0.06, `--bgm-vol` mặc định **1.2**) — nhạc LÙI dưới giọng nhưng vẫn NGHE RÕ; nhạc còn nhỏ thì
tăng `--bgm-vol`. Chưa có nhạc? **Tự gen bằng skill `music`** (ElevenLabs Music, composition plan theo cung
cảm xúc) → xuất .mp3 vào `assets/bgm/<mood>/`.

**SFX — lớp thứ 3 (consumer cho `scenes[].sfx[]`):** clip Veo TỰ sinh audio nhưng assemble luôn `-an`
(Veo hay lồng giọng-bịa tiếng Anh đè lời đọc). Muốn có hiệu ứng (gió, bước chân, khói hương, trẻ cười)
thì gen SFX SẠCH riêng rồi mix:
```bash
$PY $SK/gen_sfx.py --project projects/<tên> --scenes 2,5,14   # gen sfxNN.mp3 từ sfx[] (chọn cảnh chủ chốt)
$PY $SK/assemble.py --project projects/<tên>                  # --sfx auto: tự mix 05_audio/sfx/ dưới giọng
```
`gen_sfx.py` đọc `sfx[]` + `timings.json` → gen đúng độ dài mỗi cảnh; assemble đặt theo timing, ducking
dưới giọng, limiter chống clip. Tắt bằng `--sfx off`, chỉnh to nhỏ bằng `--sfx-vol` (mặc định 0.35).
Chọn ~6-8 cảnh chủ chốt, đừng gen cả 15 (rối tiếng). Field `sfx[]` nhờ vậy KHÔNG còn mồ côi.
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
`--fonts-dir` nếu máy thiếu font tiếng Việt · `--light` xuất thêm bản share nhẹ `*_light.mp4`
(CRF 26; thêm `--light-scale 720` để hạ 720p cho nhẹ nữa).

## Bước 2b · Motion-graphics động (opt-in — Remotion)

ffmpeg là LÕI ráp (đủ để xuất bản final). Muốn **title/hook động đẹp + end-card motion** thì phủ thêm
lớp Remotion lên `final.mp4` (background `<Video>` + overlay, render 1 lần ra `final_overlay.mp4`):
```bash
cd .agents/skills/vidgen-assemble/remotion && npm install   # lần đầu
$PY make_props.py --project ../../../projects/<tên> --endcard-text "Theo dõi để xem tiếp"
npx remotion render VidgenOverlay ../../../projects/<tên>/06_final/final_overlay.mp4 --props=props.json
```
`make_props.py` đo bản final (ffprobe) + copy bg/font vào `public/`; hookText tự lấy từ `hook.spoken`.
Chi tiết + cách tinh chỉnh: `remotion/README.md`. Không cần motion-graphics → BỎ QUA bước này.
Node deps KHÔNG commit (đã `.gitignore`). Chuẩn Remotion: skill `remotion-best-practices`.

## Bước 3 · GATE 3 (final review)

Trình user bản final + tự-QC (gate 3 — craft âm thanh/phụ đề, xem `references/caption-and-audio.md`):
☐ sub karaoke khớp giọng, 4-6 chữ, trong safe-zone ☐ chuyển cảnh khớp cảm xúc/lời
☐ nhạc ducking không đè giọng ☐ hook mở đầu mạnh ☐ không cụt đuôi ☐ đúng aspect/nền tảng đích.
**Phản biện, đừng xin gật** (`../vidgen-script/references/decision-grilling.md`): AI KHÔNG nghe
audio, KHÔNG xem chuyển động → hỏi thẳng user đúng 2 điều đó ("nhạc đè giọng chỗ nào không?
chuyển cảnh nào giật?") kèm nêu rủi ro mình chưa chắc, đừng tự kết luận "mượt rồi".
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
