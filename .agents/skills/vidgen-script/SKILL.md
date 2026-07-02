---
name: vidgen-script
description: STAGE 1 của pipeline vidgen — biến Ý TƯỞNG thành brief + kịch bản + storyboard máy-đọc-được (project.json) cho video AI gen bằng flow-agent. Dùng khi cần "lên kịch bản video", "viết storyboard", "chia cảnh", "phân cảnh video AI", "sửa kịch bản dự án vidgen", hoặc khi vidgen-flow gọi tới STEP 1. Video cho brand Akasto (bé 3-6, giọng mẹ) → dùng akasto-kichban-writer thay skill này.
---

# Vidgen Script (ý tưởng → brief → kịch bản → storyboard)

Sản phẩm của stage này là thứ RẺ NHẤT để sửa — mọi lỗi lọt qua đây sẽ đắt gấp nhiều lần
ở stage gen (tốn credit) và ráp. Vì vậy: viết kỹ, duyệt kỹ, khóa rồi mới đi tiếp.

## Bước 1 · Brief — TƯ VẤN loại video trước, đừng bắt user tự chọn

Từ ý tưởng + mục tiêu user kể, **đề xuất 1-2 loại video phù hợp kèm lý do** rồi mới hỏi
phần còn thiếu. User thường chưa biết mình cần dạng gì — đó là việc của skill này:

| Ý tưởng / mục tiêu nghe được | Đề xuất |
|---|---|
| Kể chuyện, lịch sử, giáo dục, thuyết minh | `story` 2-6' · YouTube 16:9, FB/TikTok 9:16 |
| Marketing, bán hàng, kéo reach nhanh | `reel` 9:16 20-60s, hook 3 giây, 1 CTA |
| Ru ngủ / trẻ em (không phải brand Akasto) | `story` 9:16 3-6', năng lượng đi XUỐNG về cuối |
| Giải thích khái niệm, infographic | `story` ngắn 1-2', nhiều ảnh tĩnh + Ken Burns (rẻ credit) |
| B-roll, phong cảnh, mood, không lời | `story` không VO, mode `t2v`, chỉ nhạc nền |
| Nhiều nền tảng cùng lúc | Làm bản gốc dài trước, đề xuất bản đồ repurpose 1→N |

Sau khi user chọn, chốt 5 câu bắt buộc (thiếu thì hỏi — đừng đoán): **nền tảng đích** ·
**tỉ lệ** (9:16 hay 16:9) · **thời lượng đích** · **người xem là ai** (persona cụ thể) ·
**1 mục tiêu duy nhất**. Ghi `01_script/brief.md`. Preset:
- `story` — kể chuyện 2-6 phút, 10-30 cảnh, khung 3 hồi hoặc kishōtenketsu; năng lượng
  tùy mục tiêu (ru ngủ → đi xuống, giải trí → cao trào giữa).
- `reel` — 20-60s, 4-8 cảnh; **hook 3 giây đầu** (1 lời hứa, open loop) → 1 value → 1 CTA.

## Bước 2 · Kịch bản cho người đọc

Viết `01_script/kichban.md`: lời đọc (VO) tiếng Việt từng cảnh + mô tả hình ngắn.
Câu ngắn, chủ động, đọc to lên nghe tự nhiên. **Cấm em-dash `—`** trong VO (tell AI tiếng Việt).

## Bước 3 · Storyboard máy-đọc-được

Tạo `projects/<tên>/project.json` theo schema — **đọc `references/project-schema.md`
trước khi viết file này** (quy tắc prompt, độ dài VO khớp duration, cách tách cảnh nằm ở đó).
Điền: characters (desc chi tiết), scenes (vo + prompt EN + mode + duration + characters + angle).
Mặc định `mode: "i2v"` (ảnh duyệt trước, rẻ) — cảnh thuần bối cảnh không nhân vật thì `t2v`.
Đặt `transition` từng cảnh theo CẢM XÚC của mạch kể (dissolve vào mơ, fadewhite tỉnh giấc,
fade đoạn dịu, cut nhịp nhanh — bảng trong schema) — đẹp hơn hẳn 1 kiểu đồng loạt.

## Bước 4 · Tự-QC rồi trình GATE 1 (script lock)

Tự kiểm trước khi trình user:
☐ mỗi cảnh 1 ý, VO khớp ~duration ☐ prompt EN đủ chủ thể/camera/ánh sáng, style lặp nguyên văn
☐ đặc điểm nhân vật nhắc lại trong prompt ☐ không yêu cầu chữ trong hình ☐ không em-dash
☐ tổng thời lượng khớp brief ☐ preset reel: hook 3s + CTA.
Trình user duyệt kịch bản + storyboard. User gật → set `gates.script_lock = true`. **Chưa gật thì KHÔNG gen gì cả.**

## Chạy lại / sửa

Đã có `project.json` mà user muốn sửa → chỉ sửa cảnh liên quan; cảnh đã có clip `done`
mà đổi `prompt`/`vo` thì reset `image.approved=false`, `clip.status="pending"` để stage sau gen lại đúng chỗ.
