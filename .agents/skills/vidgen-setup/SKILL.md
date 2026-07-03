---
name: vidgen-setup
description: SETUP & CHẨN ĐOÁN môi trường cho pipeline vidgen/flow-agent — kiểm tra và hướng dẫn cài từng thứ: Python venv + deps, ffmpeg (libass/xfade), Chrome extension Flow Agent, port bridge, ELEVENLABS_API_KEY, font tiếng Việt. Dùng khi user nói "setup", "cài đặt môi trường", "kiểm tra môi trường", "doctor", "chưa chạy được", "extension không kết nối", "lỗi thiếu module/filter", hoặc TRƯỚC lần đầu chạy vidgen-flow trên máy mới. Cấu hình API key ElevenLabs chi tiết → skill setup-api-key.
---

# Vidgen Setup (khám môi trường trước, khỏi vỡ giữa chừng)

Lý do tồn tại (bài học SOP): **kiểm năng lực công cụ TRƯỚC khi hứa** — giới hạn ẩn
(ffmpeg thiếu libass, ElevenLabs free bị chặn, port bận) chỉ lộ ra giữa batch nếu không khám trước.

## Bước 1 · Chạy doctor

```bash
bash .agents/skills/vidgen-setup/scripts/doctor.sh
```
Doctor CHỈ chẩn đoán, không tự sửa. Mỗi mục ❌/⚠️ in kèm đúng 1 lệnh/cách khắc phục.
Đọc kết quả rồi sửa theo thứ tự ❌ trước, ⚠️ sau (⚠️ chỉ chặn tính năng liên quan:
thiếu ELEVENLABS_API_KEY vẫn làm được video không lời).

## Bước 2 · Những thứ doctor KHÔNG kiểm được (phải làm tay 1 lần)

1. **Load extension**: Chrome → `chrome://extensions` → bật Developer mode →
   Load unpacked → chọn thư mục `extension/` ở **root repo vidgen-engine này**
   (extension đã bundle sẵn trong repo — không cần clone flow-agent).
2. **Đăng nhập Flow**: mở [labs.google/fx/tools/flow](https://labs.google/fx/tools/flow)
   bằng tài khoản Google có gói AI Pro → icon extension hiện **badge XANH** = connected.
   (Tab Flow tự mở khi chạy lệnh — không cần quản lý tab.)
3. **Credit Flow**: xem số credit còn lại trong Flow UI — video tốn credit, ảnh thì không.
4. **(Tùy chọn) Nhạc nền**: thả nhạc royalty-free vào `assets/bgm/<mood>/` để assemble tự chọn
   theo `music.mood` (xem `assets/bgm/README.md`). Bỏ qua nếu video không nhạc hoặc tự truyền `--bgm`.

## Bước 3 · Xác minh sống (tùy chọn, tốn 0 credit)

Gen thử 1 ảnh để chứng minh cả chuỗi Python → bridge → extension → Flow hoạt động:
```bash
~/.venv/claude/bin/python .agents/skills/vidgen-clips/scripts/flowgen.py t2i \
  --prompt "a red apple on white background" --out /tmp/vidgen_smoke.png
```
Ra file ảnh = môi trường sẵn sàng chạy `vidgen-flow`.

## Tra nhanh lỗi cài đặt

| Triệu chứng | Nguyên nhân → sửa |
|---|---|
| `ModuleNotFoundError` khi chạy script | Chạy sai python — luôn dùng `~/.venv/claude/bin/python`, không dùng `python3` hệ thống |
| `No such filter: 'subtitles'` | ffmpeg brew rút gọn thiếu libass → cài bản đủ; chưa cài kịp thì assemble tự xuất sub rời |
| `Address already in use` (9222/8100) | Script flow-agent cũ còn treo → `lsof -nP -iTCP:9222 -sTCP:LISTEN` rồi kill |
| `KeyError: ELEVENLABS_API_KEY` dù shell thấy | Biến set nhưng không **export** (mỗi Bash là shell mới) → thêm `export` vào `~/.zshenv` |
| ElevenLabs 401 `detected_unusual_activity` | Tier free bị chặn (proxy/VPN/nhiều acc) → cần gói trả phí |
| Extension mãi không badge xanh | Reload tab Flow, kiểm đã đăng nhập Google, xem lại Load unpacked đúng thư mục `extension/` ở root repo này |
| Muốn dùng repo flow-agent ngoài thay bản bundle | Set env `FLOW_AGENT_ROOT` hoặc ghi `vidgen.config.json`: `{"flow_agent_root": "/duong/dan/flow-agent"}` — rỗng = dùng bản bundle |
