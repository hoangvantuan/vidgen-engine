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
**RANH GIỚI môi trường→script:** nếu key báo "thiếu" dù `zsh` thấy, đó là **shell var chưa export**
(tiến trình con không nhận). Chạy qua: `zsh -lic 'export ELEVENLABS_API_KEY; $PY $SK/tts_to_ass.py ...'`.

**Đa giọng (vừa kể vừa thoại):** manifest có `scenes[].dialogue[]` → script TỰ chuyển đường per-scene
(mỗi nhân vật đọc bằng `characters[].voice_id` riêng, `--voice` là giọng narrator). `--gap` chỉnh
khoảng lặng giữa lượt (mặc định 0.25s). Không có `dialogue[]` → chạy y như cũ. Chi tiết: mục "Đa giọng"
ở `../vidgen-script/references/project-schema.md`.

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
**Hợp đồng độ dài (bài học ranh giới, ĐÃ FIX):** giọng thường NGẮN hơn video (cảnh lặng + đuôi clip).
`sidechaincompress` cắt output theo sidechain (giọng) → nhạc **tắt sớm** (từng bị: nhạc chết ở ~1:04 khi
giọng hết). Fix tại nguồn: `apad` giọng tới HẾT video **trước** sidechain
(`[1:a]apad=whole_dur=<total>,asplit=2[voc1][voc2]`) → nhạc phủ trọn; đoạn cuối không giọng thì nhạc vang
đầy tự nhiên. `amix duration=longest/first` KHÔNG cứu được (vẫn theo track ngắn sau sidechain). Verify:
`ffprobe -select_streams a:0 -show_entries stream=duration` phải ≈ độ dài video.

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

**KEO DÁN chống "mùi AI" tầng dựng (đợt 2 — 3 lớp, mặc định bật những gì an toàn):**
- **Ambience liền mạch (keo #1, mạnh nhất):** manifest có `music.ambience` (mô tả room tone EN) →
  `$PY $SK/gen_sfx.py --project ... --ambience` gen 1 file 22s → assemble TỰ loop-crossfade (không
  seam) phủ trọn video, volume thấp **không ducking** (chính sự LIÊN TỤC xuyên mọi cắt là keo —
  thiếu nó cắt rơi vào im lặng phi tự nhiên, lộ clip rời). Chỉnh `--ambience-vol` (0.25), tắt
  `--ambience off`, file riêng `--ambience <file>`.
- **Grain + LUT thống nhất (keo #2):** mỗi generation một "chất" ảnh hơi khác → `--grain` (mặc định
  5, rất nhẹ; 0=tắt) phủ nhiễu phim ĐỒNG NHẤT toàn thân video dán texture; có file grade thì
  `--lut film.cube` áp 1 màu toàn phim (ủi chênh màu giữa clip). Cả hai áp TRƯỚC burn sub (chữ sạch).
- **Trần kéo chậm (keo #3):** VO dài hơn clip → trước đây kéo chậm KHÔNG TRẦN (nguồn cảm giác
  trôi nổi slow-motion). Giờ `--max-slow` (mặc định 1.15 ≈ dưới ngưỡng mắt bắt) + phần thiếu HOLD
  frame cuối; thiếu >2s script cảnh báo ĐÚNG CẢNH — gốc ở VO/duration lệch, sửa tại storyboard,
  đừng nới trần. Chiều ngược (clip dài hơn) vẫn cắt lấy đoạn ĐẦU — chất lượng clip AI đỉnh ở 4-6s
  đầu, đuôi generation hay rã.
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

## Bước 2b · Bộ nhận diện thương hiệu — intro + end-card (Remotion, MỘT LỆNH)

Sau khi có `06_final/final.mp4`, áp brand bằng **một lệnh** → `06_final/final_overlay.mp4` (bản bàn giao):
```bash
$PY .agents/skills/vidgen-assemble/remotion/apply_brand.py --project projects/<tên> --brand <tên>
```
**Engine GENERIC — brand từ PRESET `assets/brands/<tên>/brand.json`, KHÔNG hardcode.** `apply_brand.py`
tự lo (idempotent): ① `npm install` nếu thiếu; ② **sinh lời CTA khớp tagline** bằng ElevenLabs
**`eleven_v3`** (model CÓ tiếng Việt — KHÔNG dùng `multilingual_v2`) từ giọng/spokenUrl của preset —
tagline lấy `project.json endcard_tagline` (mặc định tái dùng `cta_default.mp3` của preset);
③ tự lấy `ELEVENLABS_API_KEY` qua zsh nếu env thiếu (key không-export ở `~/.zshenv`);
④ `make_props` + `remotion render`. Tùy chọn: `--tagline` · `--voice` · `--intro-sec` · `--no-cta` · `--no-sonic`.

Kết quả: **intro** logo loang màu nước **đứng riêng** trên nền gradient brand (chạy trọn ~2s rồi
**fade qua màu nền** sang cảnh chính — KHÔNG đè lên hook), phần nội dung để **sạch** (bỏ watermark);
**end-card** nền gradient ấm + **ảnh hero nảy nở** + tagline (biến thiên theo phẩm chất) + wordmark +
url + nốt chuông + lời CTA. KHÔNG hiện hình đứa trẻ (chống over-promise, hiến pháp Mục 10).
Độ dài intro chỉnh qua `--intro-sec` hoặc `project.json intro_sec`; **`--intro-sec 0` = tắt intro**
(dùng cho bản short-form cần front-load hook ngay giây 0 — đánh đổi: mất nhận diện brand đầu video).
**Thêm brand khác:** tạo `assets/brands/<tên>/` (brand.json + 3 PNG trong suốt + sonic/cta) → `--brand <tên>`.
Chi tiết: `remotion/README.md`. Node deps KHÔNG commit. Chuẩn Remotion: skill `remotion-best-practices`.

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
