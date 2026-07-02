---
name: vidgen-character
description: STAGE 2 của pipeline vidgen — tạo NHÂN VẬT NHẤT QUÁN cho video AI: char sheet → ảnh anchor (T2I flow-agent, miễn phí) → upload lấy media_id → gen 1 clip thử → GATE character lock. Dùng khi cần "tạo nhân vật cho video", "anchor nhân vật", "char sheet", "nhân vật bị đổi mặt giữa các cảnh", "giữ nhân vật giống nhau", hoặc khi vidgen-flow gọi STEP 2.
---

# Vidgen Character (char sheet → anchor → character lock)

Nguyên lý (từ `docs/quy-trinh-tao-video-flow.md`): **char sheet cho NGƯỜI duyệt danh tính,
anchor cho MÁY bám theo**. Nạp nhầm char sheet vào Flow → AI tưởng đám đông, trộn mặt.
Ảnh T2I miễn phí — gen tới khi ưng, đừng tiếc. Video mới tốn credit.

```bash
PY=~/.venv/claude/bin/python
GEN=.agents/skills/vidgen-clips/scripts/flowgen.py   # engine dùng chung
```

## Bước 1 · Char sheet (cho người duyệt)

Mỗi nhân vật trong `project.json` → gen 1 char sheet bằng T2I:
```bash
$PY $GEN t2i --prompt "character sheet, <desc EN>, multiple angles (front, side, back), \
consistent outfit, plain white background, <style chung của dự án>" \
  --aspect landscape --out projects/<tên>/02_characters/<id>_sheet.png
```
User duyệt danh tính (mặt, trang phục, vibe) TRÊN CHAR SHEET trước — sửa ở đây rẻ nhất.

## Bước 2 · Anchor (cho máy)

Nhân vật luôn 1 góc + video ngắn → chỉ cần 1 anchor. Đổi nhiều góc → mỗi góc 1 anchor.
Gen TỪNG anchor riêng (không cắt từ sheet — chất lượng thấp):
```bash
$PY $GEN t2i --prompt "<desc EN>, front view, standing, plain white background, \
full body, single character, <style chung>" --aspect portrait \
  --out projects/<tên>/02_characters/<id>_front.png
```
Yêu cầu anchor: **1 người/ảnh · 1 góc · nền trơn · rõ mặt · style đồng bộ giữa mọi anchor**.
Lệnh in ra `media_id` → ghi ngay vào `characters[].anchors[]` trong manifest.
Ảnh có sẵn (user đưa) thì upload: `$PY $GEN upload-image path.png` → lấy media_id.

## Bước 3 · Clip thử (đốt credit NHỎ trước khi đốt LỚN)

Gen thử 1 cảnh tiêu biểu có nhân vật (chọn cảnh giữa video, đủ đại diện):
```bash
$PY $GEN scene-images --project projects/<tên> --scene <id>   # ảnh khung đầu, miễn phí
# user ưng ảnh → set image.approved=true → gen thử 1 clip:
$PY $GEN scene-clips --project projects/<tên> --scene <id> --force
```
Soi clip thử: nhân vật giống anchor? style đúng? chuyển động tự nhiên? AI-tell (thừa ngón,
mặt biến dạng)?

## Bước 4 · GATE 2 (character lock)

Trình user: char sheet + anchors + clip thử. User gật → set `gates.character_lock = true`.
Từ đây **danh tính nhân vật KHÓA** — không đổi desc/anchor giữa chừng; đổi = gen lại từ đầu.

## Chạy lại / sửa

User chê nhân vật sau khi đã lock → cảnh nào đã gen với anchor cũ phải reset
(`image.approved=false`, `clip.status="pending"`), báo rõ chi phí gen lại trước khi làm.
