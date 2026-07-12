---
name: vidgen-clips
description: STAGE 3 của pipeline vidgen — GEN CLIP HÀNG LOẠT qua flow-agent (omniflash): ảnh khung đầu từng cảnh (T2I miễn phí) → duyệt → I2V/T2V/R2V/FL (tốn credit), tự poll + tải + xóa watermark + resume theo manifest. Dùng khi cần "gen clip các cảnh", "gen lại cảnh 5", "chạy tiếp phần gen video", "batch gen video AI", hoặc khi vidgen-flow gọi STEP 3. Cần Chrome + extension Flow Agent đã kết nối.
---

# Vidgen Clips (storyboard → clip từng cảnh, resume được)

Kinh tế của stage này: **ảnh miễn phí, video tốn credit**. Vì vậy image-first:
gen ảnh khung đầu → user duyệt ảnh (rẻ) → mới I2V (đắt, 1 lần/cảnh). Mọi tiến độ ghi vào
`project.json` sau TỪNG cảnh — đứt giữa chừng chạy lại không mất gì, không gen trùng.

**BA ĐƯỜNG GEN theo số thực thể cần neo** (ngân sách 3 ref/generation — bảng đầy đủ + luật ưu
tiên slot: `project-schema.md` mục "Ba đường gen"):
1. Cảnh thường (≤2 nhân vật mặt rõ + location) → **i2v từ ảnh đã duyệt** (Bước 1-2 dưới).
2. Cảnh coverage `shots[]` → **r2v + anchor** (nhân vật > hero-prop > location; `ref_prev` thay
   location anchor khi cắt đổi góc cùng không gian).
3. Cảnh ĐÔNG (`composite: true`) → **compose-frame** ghép dần từng thực thể vào khung đầu
   (miễn phí, mỗi lượt ≤3 ref TÍCH LŨY) → duyệt khung → i2v như thường:
   ```bash
   $PY $GEN compose-frame --project projects/<tên> --scene 4   # 1 cảnh/lần, duyệt từng khung
   ```
   Khung cuối lệch → soi từng lượt `03_images/sceneNN_comp_K.png` tìm lượt hỏng, sửa rồi chạy lại.
**LUẬT chất lượng: mọi khung đầu (kể cả composite, kể cả khung chain) phải NGƯỜI duyệt trước khi
đốt credit.**

**Craft prompt (đọc trước khi gen/soi):** công thức prompt Veo 5 phần, vựng camera/cỡ cảnh, negative
prompt tránh AI-tell, cách né chặn nội dung → `references/veo-prompt-craft.md`. Veo 3 còn **sinh
audio (SFX/ambience) ngay từ prompt** — hữu ích cho cảnh không lời đọc.

```bash
PY=~/.venv/claude/bin/python
GEN=.agents/skills/vidgen-clips/scripts/flowgen.py
```

## Điều kiện chạy

- Chrome mở + extension Flow Agent kết nối (script tự mở tab Flow, tự retry 3 lần).
- `gates.script_lock = true` (kịch bản đã duyệt); gen hàng loạt cần thêm `character_lock = true`
  (script tự chặn, `--force` chỉ dùng cho clip thử ở stage 2).
- Port 9222/8100 rảnh (bận = `python -m cli.api` hoặc flowgen cũ còn treo; flowgen nay báo rõ cách kill).
- **Đang batch thì hạn chế sửa tay `project.json`**: script re-load + chỉ ghi field nó sở hữu
  (image/clip) nên sửa field/cảnh KHÁC vẫn an toàn — chỉ tránh sửa đúng cảnh đang gen dở.

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

**Frame-chaining (chuyển cảnh LIỀN MẠCH):** cảnh nào đặt `link_prev: true` trong manifest thì
`scene-clips` tự trích **khung cuối NÉT nhất** của clip cảnh trước (chọn theo độ nét, chống
motion-blur) → dùng làm khung đầu cảnh này → không gian/chuyển động nối liền, chỉ cần xfade nhẹ là
mượt. Ràng buộc: **gen TUẦN TỰ** (cảnh trước phải xong trước — cùng run hoặc run trước), nên tránh
`--scene N` lẻ làm đứt chuỗi. Chỉ bật cho cặp cảnh CÙNG mạch/bối cảnh; đổi cảnh hoàn toàn thì để `false`
và dùng transition biên tập (cut/match cut) ở Stage 4.
**Duyệt khung chain TRƯỚC khi đốt credit** (luật khung-đầu-phải-qua-mắt-người):
```bash
$PY $GEN extract-chain --project projects/<tên>    # trích sẵn mọi khung chain/refprev → duyệt
```
Khung xấu (mờ, AI-tell, sai bối cảnh) → xoá file để trích lại hoặc tắt link_prev cảnh đó.
`scene-clips` thấy file đã tồn tại thì DÙNG LẠI (không trích đè); chạy thẳng scene-clips không
extract trước vẫn được nhưng sẽ in ⚠ "chưa qua duyệt".

**ref_prev (đồng bộ ánh sáng/layout khi CẮT ĐỔI GÓC cùng không gian, mode r2v):** frame cuối nét
cảnh trước vào slot ref, **THAY location anchor**. 2 luật an toàn: danh tính LUÔN từ anchor gốc
(chống trôi photocopy qua nhiều đời frame); chỉ chain/ref từ clip đã qua qc-clips (chống AI-tell
lây lan). Khác link_prev: không ép liền mạch chuyển động, chỉ mượn không gian.

## Bước 3 · QC CONTINUITY trên clip thật (chốt chặn cuối trước ráp — máy trích, Claude soi, người quyết)

```bash
$PY $GEN qc-clips --project projects/<tên>    # trích frame đầu/giữa/cuối-nét mỗi clip + ledger.md
```
Rồi Claude **Read `qc_clips/ledger.md` + các frame PNG**, đối chiếu theo checklist trong ledger:
mặt khớp anchor? trang phục khớp `state.wardrobe`? prop đúng desc registry? ánh sáng khớp
time_of_day VÀ khớp cảnh liền kề cùng location? layout bối cảnh liền? AI-tell? → báo user **danh
sách lệch per cảnh** (lệch gì, so với nguồn sự thật nào) — NGƯỜI quyết regen (mandate chất lượng:
credit đổi lấy đồng bộ, regen không tiếc nhưng người bấm nút).
Soi tay bổ sung mỗi clip: ☐ chuyển động không giật ☐ không chữ lạ trong hình ☐ đúng aspect
☐ **không còn dấu watermark**.
Clip hỏng → sửa prompt cảnh đó → `--scene N --regen`; hoặc CHỈ lỗi nhỏ → sửa bằng **v2v** (mục "Lệnh lẻ").
Regen xong CHẠY LẠI qc-clips cho cảnh đó (regen là xúc xắc — có thể lệch kiểu khác).

**Watermark Veo sót → delogo trước khi ráp (bài học ranh giới, vị trí CỐ ĐỊNH):** dù pipeline đã "xóa
watermark", Veo/Flow vẫn để sót **ngôi sao 4 cánh (sparkle ✦)** góc dưới–phải. Vị trí ổn định trên khung
gốc **720×1280**: `delogo=x=572:y=1128:w=92:h=104`. Trước khi assemble, delogo mọi clip (backup gốc):
`ffmpeg -i raw.mp4 -vf "delogo=x=572:y=1128:w=92:h=104" -c:v libx264 -crf 18 out.mp4`. Soi lại 2-3 clip
sau delogo (crop góc dưới–phải) để chắc phủ đúng — Flow đổi version có thể dịch vị trí. Regen clip là phải
delogo LẠI (clip mới có watermark).

## Lệnh lẻ (ngoài pipeline)

`flowgen.py` cũng dùng độc lập được: `t2i` (ảnh nhanh), `upload-image`, `clip --mode t2v|i2v|r2v|fl|v2v`
(1 clip lẻ). Xem `$PY $GEN --help`.
**Sửa clip đã có (v2v) — khỏi gen lại từ đầu, tiết kiệm credit:**
`clip --mode v2v --video-id <media_id> --prompt "đổi X thành Y"` (media_id lấy từ
`scenes[].clip.media_id` trong manifest), hoặc `--video-file clip.mp4` (upload video local rồi sửa).

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
