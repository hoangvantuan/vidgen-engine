# Brand presets — bộ nhận diện cho overlay video

Mỗi thư mục con = **một brand**. Engine Remotion (`.agents/skills/vidgen-assemble/remotion/`) đọc
preset ở đây, **không hardcode brand nào**. Áp brand:

```bash
~/.venv/claude/bin/python .agents/skills/vidgen-assemble/remotion/apply_brand.py \
  --project projects/<tên> --brand <tên-brand>
```

## Thêm brand mới (KHÔNG đụng code)

Tạo `assets/brands/<tên>/` gồm:

| File | Bắt buộc | Là gì |
|---|---|---|
| `brand.json` | ✅ | config (dưới) |
| `logo_lockup.png` | ✅ | logo đầy đủ, **nền trong suốt** — intro bloom |
| `logo_mark.png` | ✅ | chỉ biểu tượng, **trong suốt** — watermark góc |
| `hero.png` | ✅ | ảnh hero end-card, **trong suốt** — nở từ gốc lên |
| `sonic_chime.mp3` | tùy chọn | nốt chuông brand |
| `cta_default.mp3` | tùy chọn | lời CTA cho tagline mặc định (tái dùng, khỏi gọi API) |

`brand.json`:
```json
{
  "wordmark": "Tên Brand",
  "ctaUrl": "brand.com",
  "spokenUrl": "brand chấm com",
  "voice": "<ElevenLabs voice id — giọng tiếng Việt>",
  "defaultTagline": "Câu tagline mặc định.",
  "colors": { "bgTop": "#RRGGBB", "bgBottom": "#RRGGBB", "text": "#RRGGBB" },
  "assets": { "logoLockup": "logo_lockup.png", "logoMark": "logo_mark.png",
              "hero": "hero.png", "sonic": "sonic_chime.mp3", "ctaDefault": "cta_default.mp3" }
}
```

**Lưu ý:**
- PNG phải **trong suốt thật** (RGBA). Nền trắng/ô-cờ baked sẽ lòi ra — key nền trước khi đưa vào.
- `voice` phải chạy với model **`eleven_v3`** (apply_brand cố định) — model có tiếng Việt.
- End-card hiện là **một template** (hero nở + wordmark + url). Muốn kiểu khác → thêm template ở
  `VidgenOverlay.tsx` (chọn qua field mới trong brand.json).

## Preset hiện có

- (chưa có preset nào ship sẵn) — tạo `assets/brands/<tên>/` theo bảng trên để thêm brand.
