# Vidgen Overlay (Remotion) — bộ nhận diện thương hiệu trên final.mp4

**Vai trò:** ffmpeg (`assemble.py`) là LÕI ráp (retime khớp giọng, frame-chain, xfade, ducking,
burn sub) → xuất `final.mp4`. Remotion phủ **bộ nhận diện thương hiệu** lên trên. Bản final ffmpeg
thành background `<Video>` (phần NỘI DUNG), render 1 lần ra `final_overlay.mp4`.

**Engine GENERIC — brand đến từ PRESET, KHÔNG hardcode.** Mọi giá trị brand (màu, wordmark, url,
giọng, asset) nằm ở `assets/brands/<tên>/brand.json`. Đổi/ thêm brand = thêm preset, KHÔNG sửa code.

## Chạy — MỘT LỆNH (khuyến nghị)

```bash
~/.venv/claude/bin/python .agents/skills/vidgen-assemble/remotion/apply_brand.py \
  --project projects/<tên> --brand <tên-brand>
```
`apply_brand.py` tự lo: `npm install` nếu thiếu → sinh lời CTA khớp tagline (ElevenLabs **eleven_v3**)
→ `make_props` → `remotion render` → `06_final/final_overlay.mp4`. Tùy chọn: `--tagline "..."` ·
`--voice <id>` · `--no-cta` · `--no-sonic`. Tự lấy `ELEVENLABS_API_KEY` qua zsh nếu env thiếu.

## Thiết kế (chốt qua grilling — xem AGENTS.md)

- **Intro (giây 0–1.7):** logo lockup **loang màu nước** (bloom) rồi **co + trượt lên góc trên–trái**
  **lắng thành watermark** — một phần tử, KHÔNG giây chết (nội dung/lời chạy ngay giây 0).
- **Watermark:** biểu tượng mờ (~42%) góc trên–trái suốt phần nội dung (né sub + UI TikTok).
- **End-card (CỘNG THÊM):** nền gradient ấm (từ `colors`) + **ảnh hero NẢY NỞ** (reveal mask từ gốc
  lên, `heroImg` của preset) + **tagline biến thiên** + **wordmark** + **url**. KHÔNG hiện hình đứa
  trẻ (chống over-promise, hiến pháp Mục 10).
- **Âm thanh:** nốt chuông intro (duck 0.28 dưới lời) + lời CTA cuối (bg đã hết → sạch) + chuông đóng
  khung. Đều tùy chọn.

## Preset brand — `assets/brands/<tên>/`

```
assets/brands/<tên>/
  brand.json          # config (dưới)
  logo_lockup.png     # logo đầy đủ, TRONG SUỐT (intro bloom)
  logo_mark.png       # chỉ biểu tượng, TRONG SUỐT (watermark)
  hero.png            # ảnh hero end-card, TRONG SUỐT (nở từ gốc)
  sonic_chime.mp3     # nốt chuông
  cta_default.mp3     # lời CTA cho tagline mặc định (tái dùng, khỏi gọi API)
```

`brand.json`:
```json
{
  "wordmark": "Your Brand",
  "ctaUrl": "yourbrand.com",
  "spokenUrl": "your brand chấm com",       // cách ĐỌC url cho TTS
  "voice": "<ElevenLabs voice id — giọng tiếng Việt>",
  "defaultTagline": "Câu tagline mặc định.",
  "colors": { "bgTop": "#FDF6EC", "bgBottom": "#FBE4D2", "text": "#3E5A87" },
  "assets": { "logoLockup": "logo_lockup.png", "logoMark": "logo_mark.png",
              "hero": "hero.png", "sonic": "sonic_chime.mp3", "ctaDefault": "cta_default.mp3" }
}
```

**Thêm brand mới:** tạo `assets/brands/<tên>/` với `brand.json` + 3 PNG TRONG SUỐT (logo_lockup/
logo_mark/hero) + (tùy chọn) sonic/cta_default → `apply_brand.py --brand <tên>`. KHÔNG đụng code.
PNG phải TRONG SUỐT thật (RGBA) — nếu logo/hero gốc nền trắng/ô-cờ baked thì key nền trước khi đưa vào.

**⚠ Lời CTA (TTS) PHẢI dùng model có tiếng Việt** — `eleven_v3`/`eleven_flash_v2_5`/`eleven_turbo_v2_5`.
KHÔNG dùng `eleven_multilingual_v2` (không có `vi` → đọc lơ lớ). apply_brand đã cố định `eleven_v3`.

## Cấu trúc code

- `src/Root.tsx` — Composition `VidgenOverlay`; `calculateMetadata` lấy duration/kích thước từ props.
- `src/VidgenOverlay.tsx` — GENERIC: `<Video>` nền + `IntroLogo` + `Watermark` + `EndCard` (hero nở +
  `BrandFooter`). Màu/asset/text đều là PROPS. Animation `interpolate`/`useCurrentFrame`.
- `make_props.py` — nạp `brand.json` (--brand-config) + ffprobe bản nội dung → props.json + copy asset
  preset vào `public/`. Đo tỉ lệ hero từ header PNG → `heroAspect`. Cộng end-card vào tổng.
- `apply_brand.py` — MỘT LỆNH orchestrate (resolve preset, sinh CTA, make_props, render).

**Không commit node_modules** (`.gitignore` đã loại `node_modules/`, `public/`, `props.json`).
Chuẩn Remotion: skill `remotion-best-practices`.
