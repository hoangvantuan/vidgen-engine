# Schema `project.json` — manifest dự án vidgen

Manifest là NGUỒN SỰ THẬT duy nhất về trạng thái dự án. Script chỉ ghi các field nó sở hữu
(`media_id`, `status`); Claude sửa phần còn lại bằng Edit. Ghi atomic — an toàn khi hỏng giữa chừng.

```json
{
  "name": "con-cao-va-chum-nho",
  "preset": "story",                    // "story" (kể chuyện dài) | "reel" (ngắn 20-60s)
  "aspect": "portrait",                 // "portrait" 9:16 | "landscape" 16:9
  "language": "vi",
  "voice_id": "",                       // ElevenLabs voice id (rỗng = video không lời đọc)
  "flow_project_id": "",                // rỗng = dùng DEFAULT_PROJECT của omniflash

  "hook": {                             // MỞ ĐẦU — nơi tụt người xem mạnh nhất (short-form ~3s, long-form ~30s)
    "promise": "",                      // lời hứa/tò mò khán giả nhận NGAY giây đầu (open loop)
    "first_frame": "",                  // mô tả frame hình đầu tiên gây tò mò → đưa vào prompt cảnh mở
    "spoken": ""                        // câu VO đầu tiên, mạnh nhất — đặt lên đầu
  },
  "music": {                            // nhạc nền — auto-pick theo mood hoặc chỉ định file
    "mood": "",                         // calm|tense|uplifting|sad|epic|playful|neutral (rỗng = không nhạc)
    "file": ""                          // nhạc cụ thể (ưu tiên hơn mood; CLI --bgm override cả hai)
  },

  "gates": {                            // 3 cổng human — orchestrator kiểm trước khi đi tiếp
    "script_lock": false,               // GATE 1: kịch bản + storyboard đã duyệt
    "character_lock": false,            // GATE 2: anchor + clip thử đã duyệt
    "final_approved": false             // GATE 3: bản ráp cuối đã duyệt
  },

  "characters": [
    {
      "id": "be_na",
      "desc": "bé gái 5 tuổi, tóc hai bím, váy vàng, mắt to",   // NHẮC LẠI trong prompt mỗi cảnh
      "sheet": "02_characters/be_na_sheet.png",                 // char sheet — cho NGƯỜI duyệt, KHÔNG nạp vào Flow
      "anchors": [                                              // anchor — cho MÁY: 1 người/ảnh, 1 góc, nền trơn
        { "angle": "front", "file": "02_characters/be_na_front.png", "media_id": "" },
        { "angle": "side",  "file": "02_characters/be_na_side.png",  "media_id": "" }
      ]
    }
  ],

  "scenes": [
    {
      "id": 1,
      "vo": "Lời đọc tiếng Việt của cảnh này.",   // rỗng nếu video không lời
      "prompt": "English visual prompt: subject, action, camera, lighting, style. NO text overlay.",
      "mode": "i2v",                    // "i2v" (mặc định) | "t2v" | "r2v" | "fl"
      "duration": 8,                    // 4|6|8|10 — thời lượng gen; khi ráp sẽ setpts khớp lời đọc
      "characters": ["be_na"],          // id nhân vật xuất hiện → flowgen tự chọn anchor làm ref
      "angle": "front",                 // góc nhân vật trong cảnh → chọn anchor đúng góc
      "role": "hook",                   // (tùy chọn) vai trò mạch kể: hook|setup|development|turn|payoff|cta
      "shot_size": "medium",            // (tùy chọn) cỡ cảnh: wide|medium|close|extreme_close|establishing — ĐA DẠNG giữa các cảnh
      "camera_move": "push_in",         // (tùy chọn) chuyển máy: static|push_in|pull_out|pan|tilt|orbit|handheld|crane
      "image": { "file": "03_images/scene01.png", "media_id": "", "approved": false },
      "end_image": { "media_id": "" },  // chỉ mode "fl"
      "clip": { "file": "04_clips/scene01.mp4", "media_id": "", "status": "pending" },
      // clip.status: "pending" | "done" | "failed"
      "transition": { "type": "fade", "dur": 0.5 }
      // chuyển cảnh SAU cảnh này (sang cảnh kế) — chọn theo CẢM XÚC, không đồng loạt 1 kiểu:
      // "dissolve" vào mơ/hồi tưởng · "fadewhite" tỉnh giấc/nhảy thời gian · "fade" đoạn dịu
      // · "cut" (hoặc bỏ field) nhịp nhanh/hành động. dur giữ 0.4-0.6s để không phá timing.
    }
  ],

  "final": "06_final/final.mp4"
}
```

## Cấu trúc thư mục chuẩn (script tự tạo khi cần)

```
projects/<tên>/
├── project.json        # manifest này
├── 01_script/          # brief.md + kichban.md (bản cho người đọc/duyệt)
├── 02_characters/      # char sheet + anchors
├── 03_images/          # ảnh khung đầu từng cảnh (T2I — miễn phí, gen tới khi ưng)
├── 04_clips/           # clip từng cảnh (I2V — tốn credit, chỉ gen sau khi duyệt ảnh)
├── 05_audio/           # narration.mp3 + subs.ass + timings.json
└── 06_final/           # final.mp4
```

## Quy tắc điền storyboard (chống lỗi hay gặp)

- `prompt` viết **tiếng Anh**, tả đủ: chủ thể + hành động + camera + ánh sáng + style chung.
  **Nhắc lại đặc điểm nhân vật** (từ `characters[].desc`) trong prompt — đừng chỉ dựa vào ảnh ref.
- **KHÔNG yêu cầu chữ trong hình** (sub burn sau khi ráp). `flowgen scene-images` TỰ nối
  "no text, no watermark…" vào prompt (AI hay tự bịa chữ/thư pháp dù không yêu cầu) — tắt bằng `--allow-text`.
- **Continuity địa điểm:** cảnh liền kề CÙNG bối cảnh → lặp **nguyên văn** cụm mô tả địa điểm
  (đừng để cảnh sau đổi setting bất ngờ vì prompt không ràng buộc địa điểm với cảnh trước).
- Style chung (art style, palette, lighting) lặp NGUYÊN VĂN ở mọi prompt → các cảnh đồng bộ.
- Đổi góc nhân vật → tách cảnh mới, đặt `angle` đúng.
- 1 cảnh = 1 ý = 1 chuyển động chính, 4-10s. Cảnh không nhân vật → `mode: "t2v"`, bỏ `characters`.
- `vo` mỗi cảnh nên đọc hết trong ~`duration` giây (tiếng Việt ~3-4 chữ/giây;
  cảnh 8s ≈ 24-30 chữ). Lệch nhiều thì khi ráp clip bị kéo/nén quá tay.

## Field craft (Mức 3 — TÙY CHỌN, backward-compatible)

Các field dưới đây **không bắt buộc** — dự án cũ thiếu chúng vẫn chạy y nguyên. Khi có, script
dùng để nâng chất lượng. Nền tảng bằng chứng nằm ở các file `references/` của từng skill (đọc
trước khi điền — đã lọc số liệu bịa, chỉ giữ kỹ thuật có nguồn):

- **`hook`** (project-level) — mở đầu là nơi tụt người xem mạnh nhất: short-form quyết trong
  **~3 giây** ("swipe or stay"), long-form tụt mạnh nhất **15-30 giây** đầu (YouTube Help: intro
  đo bằng % còn xem sau 30s). Điền `promise`/`first_frame`/`spoken` để dồn lực vào đây; cảnh mở
  đặt `role: "hook"`. Chi tiết: `vidgen-script/references/hook-and-structure.md`.
- **`role`** (scene) — vai trò cảnh trong mạch kể (3 hồi, hoặc kishōtenketsu 4 phần
  ki→shō→ten→ketsu cho video KHÔNG dựa xung đột). Cho biết cảnh nào là hook (đầu tư nhất) / payoff.
- **`shot_size`** (scene) — cỡ cảnh; **đa dạng giữa các cảnh liền kề** cho nhịp thị giác. Đưa
  thẳng vào `prompt` (Veo hiểu "wide establishing shot", "medium shot", "close-up"). Đừng để mọi
  cảnh cùng một cỡ.
- **`camera_move`** (scene) — chuyển động máy có chủ đích, đưa vào `prompt` (Veo hiểu "slow
  push-in", "180-degree orbit", "handheld", "static"). Vựng từ đầy đủ:
  `vidgen-clips/references/veo-prompt-craft.md`.
- **`music.mood`** (project-level) — assemble tự chọn nhạc nền khớp mood từ `assets/bgm/`, hoặc
  `music.file` chỉ định tay. Chi tiết: `vidgen-assemble/references/caption-and-audio.md`.
