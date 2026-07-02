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

  "audio": { "bgm": "" },               // đường dẫn nhạc nền (tùy chọn)
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
- **KHÔNG yêu cầu chữ trong hình** (sub burn sau khi ráp).
- Style chung (art style, palette, lighting) lặp NGUYÊN VĂN ở mọi prompt → các cảnh đồng bộ.
- Đổi góc nhân vật → tách cảnh mới, đặt `angle` đúng.
- 1 cảnh = 1 ý = 1 chuyển động chính, 4-10s. Cảnh không nhân vật → `mode: "t2v"`, bỏ `characters`.
- `vo` mỗi cảnh nên đọc hết trong ~`duration` giây (tiếng Việt ~3-4 chữ/giây;
  cảnh 8s ≈ 24-30 chữ). Lệch nhiều thì khi ráp clip bị kéo/nén quá tay.
