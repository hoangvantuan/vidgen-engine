---
name: vidgen-clips
description: STAGE 3 của pipeline vidgen — GEN CLIP HÀNG LOẠT qua flow-agent (omniflash): ảnh khung đầu từng cảnh (T2I miễn phí) → duyệt → I2V/T2V/R2V/FL (tốn credit), tự poll + tải + xóa watermark + resume theo manifest. Dùng khi cần "gen clip các cảnh", "gen lại cảnh 5", "chạy tiếp phần gen video", "batch gen video AI", hoặc khi vidgen-flow gọi STEP 3. Cần Chrome + extension Flow Agent đã kết nối.
---

# Vidgen Clips (storyboard → clip từng cảnh, resume được)

Kinh tế của stage này: **ảnh miễn phí, video tốn credit**. Vì vậy image-first:
gen ảnh khung đầu → user duyệt ảnh (rẻ) → mới I2V (đắt, 1 lần/cảnh). Mọi tiến độ ghi vào
`project.json` sau TỪNG cảnh — đứt giữa chừng chạy lại không mất gì, không gen trùng.

```bash
PY=~/.venv/claude/bin/python
GEN=.agents/skills/vidgen-clips/scripts/flowgen.py
```

## Điều kiện chạy

- Chrome mở + extension Flow Agent kết nối (script tự mở tab Flow, tự retry 3 lần).
- `gates.script_lock = true` (kịch bản đã duyệt); gen hàng loạt cần thêm `character_lock = true`
  (script tự chặn, `--force` chỉ dùng cho clip thử ở stage 2).
- Port 9222/8100 rảnh (lỗi "Address already in use" → kill script cũ trước).

## Bước 1 · Ảnh khung đầu (miễn phí — vòng lặp duyệt)

```bash
$PY $GEN scene-images --project projects/<tên>            # mọi cảnh i2v/fl chưa có ảnh duyệt
$PY $GEN scene-images --project projects/<tên> --scene 3 7  # gen lại cảnh cụ thể
```
Script tự lấy anchor nhân vật (đúng góc `angle`) làm ref, tối đa 3 ref/cảnh.
Trình ảnh cho user theo LÔ (mọi cảnh một lượt) — ưng cảnh nào set `image.approved=true`
cảnh đó, chưa ưng thì sửa prompt trong manifest rồi gen lại đúng cảnh ấy.

## Bước 2 · Gen clip hàng loạt (TỐN credit — báo số lượng trước khi chạy)

Trước khi chạy, nói rõ với user: sẽ gen N clip ≈ N lần credit. Rồi:
```bash
$PY $GEN scene-clips --project projects/<tên>             # mọi cảnh đủ điều kiện, bỏ qua done
$PY $GEN scene-clips --project projects/<tên> --scene 5 --regen   # gen lại 1 cảnh
```
Mỗi cảnh: submit → poll (~44s-vài phút) → tải → xóa watermark → ghi manifest.
Lỗi tự retry 1 lần; vẫn hỏng → `status: "failed"`, chạy tiếp cảnh khác (không chết cả batch).
Xong batch báo user danh sách failed để quyết: gen lại / sửa prompt / bỏ cảnh.

## Bước 3 · QC nhanh trước khi sang ráp

Xem từng clip trong `04_clips/`: ☐ nhân vật khớp anchor ☐ chuyển động không giật/AI-tell
☐ không chữ lạ trong hình ☐ đúng aspect. Clip hỏng → sửa prompt cảnh đó → `--scene N --regen`.

## Lệnh lẻ (ngoài pipeline)

`flowgen.py` cũng dùng độc lập được: `t2i` (ảnh nhanh), `upload-image`, `clip --mode t2v|i2v|r2v|fl`
(1 clip lẻ). Xem `$PY $GEN --help`.

## Sự cố hay gặp

| Hiện tượng | Xử lý |
|---|---|
| Extension không kết nối | Mở Chrome, đăng nhập Flow, chờ badge xanh |
| `No media in response` | Prompt bị chặn — viết lại prompt trung tính hơn |
| `500 Failed to download` LẶP ≥2 lần cùng 1 cảnh | Veo chặn NGẦM nội dung ảnh (người trong suốt/ma/spirit, phát sáng xuyên thấu…). KHÔNG retry quá 2-3 lần — đổi concept ảnh cảnh đó, hoặc cứ để `failed`: vidgen-assemble tự fallback Ken Burns từ ảnh tĩnh |
| Hết credit | Báo user; ảnh (T2I) vẫn gen được, chỉ video dừng |
| TIMEOUT khi poll | Reload tab Flow, chạy lại — manifest giữ tiến độ |
| Nhầm port khi dùng API server | Bridge callback ở **8100**, FastAPI ở **8000** — đừng đoán: `lsof -p <pid>` + đọc `/openapi.json` lấy route thật |

**Đặc tính output Flow (biết trước đỡ ngạc nhiên):** clip trả về **720×1280** (không phải
1080×1920 — assemble tự scale cover lên) và **Veo tự gắn audio gốc** vào clip (assemble tự `-an`).
