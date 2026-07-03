# Vidgen Overlay (Remotion) — opt-in motion-graphics trên final.mp4

**Vai trò:** ffmpeg (`assemble.py`) vẫn là LÕI ráp (retime khớp giọng, frame-chain, xfade, ducking,
burn sub) → xuất `final.mp4`. Remotion **tùy chọn** thêm lớp motion-graphics đẹp lên trên: **title/hook
động** ở đầu + **end-card** cuối. Bản final ffmpeg trở thành background `<Video>`, render 1 lần ra
`final_overlay.mp4`. Không dùng thì bỏ qua — pipeline vẫn chạy đủ bằng ffmpeg.

**Không commit node_modules** — cài khi cần (`.gitignore` đã loại `node_modules/`, `public/`, `props.json`).

## Dùng (khi user muốn title/end-card động)

```bash
cd .agents/skills/vidgen-assemble/remotion
npm install                                   # lần đầu (nặng, cần mạng)

# 1. Sinh props từ project.json + final.mp4 (đo duration, copy bg + font vào public/)
python make_props.py --project ../../../projects/<tên> \
  --endcard-text "Theo dõi để xem tiếp" --title-sec 3 --endcard-sec 3
#   hookText tự lấy từ project.json hook.spoken/promise; override bằng --hook "..."

# 2. Preview (tùy chọn) hoặc render thẳng
npx remotion studio                           # xem/tinh chỉnh trong Studio
npx remotion render VidgenOverlay ../../../projects/<tên>/06_final/final_overlay.mp4 --props=props.json
```

## Cấu trúc

- `src/Root.tsx` — Composition `VidgenOverlay`; `calculateMetadata` lấy duration/kích thước từ props.
- `src/VidgenOverlay.tsx` — background `<Video>` + `TitleCard` (đầu) + `EndCard` (cuối). Animation
  bằng `interpolate`/`useCurrentFrame` (KHÔNG spring/CSS-anim — theo chuẩn Remotion). Font Be Vietnam
  Pro nạp qua `@font-face` + `staticFile` để giữ dấu tiếng Việt khi render.
- `make_props.py` — cầu nối: ffprobe bản final → props.json + copy `public/bg.mp4`, `public/*.ttf`.

## Chỉnh sửa thường gặp

- Đổi vị trí/màu/size title → sửa `TitleCard`/`EndCard` trong `VidgenOverlay.tsx`.
- Thêm logo brand vào end-card → `<Img src={staticFile("logo.png")}/>` (đặt logo vào `public/`).
- Hiệu ứng nâng cao (light leak, glow…) → xem skill `remotion-best-practices` (rules/effects.md).
