---
name: vidgen-script
description: STAGE 1 của pipeline vidgen — biến Ý TƯỞNG thành brief + kịch bản + storyboard máy-đọc-được (project.json) cho video AI gen bằng flow-agent. Dùng khi cần "lên kịch bản video", "viết storyboard", "chia cảnh", "phân cảnh video AI", "sửa kịch bản dự án vidgen", hoặc khi vidgen-flow gọi tới STEP 1. Video cho brand Akasto (bé 3-6, giọng mẹ) → dùng akasto-kichban-writer thay skill này.
---

# Vidgen Script (ý tưởng → brief → kịch bản → storyboard)

Sản phẩm của stage này là thứ RẺ NHẤT để sửa — mọi lỗi lọt qua đây sẽ đắt gấp nhiều lần
ở stage gen (tốn credit) và ráp. Vì vậy: viết kỹ, duyệt kỹ, khóa rồi mới đi tiếp.

## Bước 1 · Brief — PHỎNG VẤN quyết định (grilling), đừng bắt user tự chọn

**Cách hỏi (bắt buộc — đọc `references/decision-grilling.md`):** brief là tầng RẺ NHẤT để
sửa; grill kỹ ở đây để moi giả định ngầm trước khi nó thành clip hỏng. Đi theo **cây quyết
định 5 nhánh** (mục tiêu duy nhất → persona → loại video → nền tảng/tỉ lệ → thời lượng),
**hỏi từng câu một, mỗi câu kèm đề xuất + 1 rủi ro nếu chọn sai** — KHÔNG bắn cả 5 câu một
lượt. Câu nào user đã nói rõ / suy được từ context → tự chốt, chỉ nhắc lại 1 dòng "mình hiểu
là …" để user kịp bắt lỗi; chỉ bung phỏng vấn ở nhánh mơ hồ hoặc chọn sai thì đắt.

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

5 thông tin bắt buộc chốt qua phỏng vấn (KHÔNG hỏi dồn một lượt — theo thứ tự dependency ở
`decision-grilling.md`): **1 mục tiêu duy nhất** (gốc) → **người xem là ai** (persona cụ thể)
→ loại video → **nền tảng đích** → **tỉ lệ** (9:16 hay 16:9) → **thời lượng đích**. Thiếu thì
hỏi (kèm đề xuất), đừng đoán. Ghi `01_script/brief.md`. Preset:
- `story` — kể chuyện 2-6 phút, 10-30 cảnh, khung 3 hồi hoặc kishōtenketsu; năng lượng
  tùy mục tiêu (ru ngủ → đi xuống, giải trí → cao trào giữa).
- `reel` — 20-60s, 4-8 cảnh; **hook 3 giây đầu** (1 lời hứa, open loop) → 1 value → 1 CTA.

**Thiết kế HOOK (bắt buộc — nơi giữ/mất người xem):** short-form quyết trong **~3 giây**, long-form
tụt mạnh nhất **15-30s** đầu (YouTube đo intro = % còn xem sau 30s). Điền khối `hook`
(`promise`/`first_frame`/`spoken`) trong manifest; đặt câu VO mạnh nhất + frame tò mò LÊN ĐẦU. Mẫu
hook + cấu trúc kể (3 hồi / kishōtenketsu): đọc `references/hook-and-structure.md`.

## Bước 2 · Kịch bản cho người đọc — viết LỜI cho tai

Viết `01_script/kichban.md`: lời đọc (VO) tiếng Việt từng cảnh + mô tả hình ngắn.
Câu ngắn, chủ động, đọc to lên nghe tự nhiên. **Cấm em-dash `—`** trong VO (tell AI tiếng Việt).

**Craft tầng ngôn từ (bắt buộc đọc `references/vo-writing-craft.md`):** cấu trúc đúng chưa đủ — lời
viết PHẲNG thì hình đẹp mấy cũng không giữ được người xem. File đó dạy 7 việc kèm before/after: ①
hook execution (câu đầu không dạo đầu) ② open-loop laddering (cấy lực kéo, chống kể tuyến tính rời)
③ biến thiên nhịp (câu cụt để đấm, chống ngắn đều buồn tẻ) ④ show-don't-tell (chi tiết gánh, cắt
tính từ cảm xúc) ⑤ dấu lặng (cảnh không lời cho hình thở) ⑥ khoá 1 through-line ⑦ viết thoại lồng
tiếng. **Test xuyên suốt: ĐỌC TO** — vấp/nghe như văn viết thì sửa (TTS đọc y như bạn viết).

**Video có nhân vật NÓI CHUYỆN thật (vừa kể vừa thoại):** pipeline hỗ trợ **lồng tiếng đa giọng** —
narrator đọc `vo`, mỗi nhân vật một giọng riêng đọc `dialogue[]`. Kiểu dub (KHÔNG khớp miệng). Cách
khai báo + luật viết: mục "Đa giọng" trong `references/project-schema.md` và mục ⑦ ở `vo-writing-craft.md`.

## Bước 3 · Storyboard máy-đọc-được (điền FIELD → compiler ghép prompt)

Tạo `projects/<tên>/project.json` theo schema — **đọc `references/project-schema.md`
trước khi viết file này** (quy tắc field, độ dài VO khớp duration, cách tách cảnh, cơ chế compiler).
Điền: `characters` (desc chi tiết; **`voice_id` nếu nhân vật có thoại** — xem dưới), `locations`
(nếu khoá bối cảnh), `style` chung, scenes. Mặc định `mode: "i2v"` (ảnh duyệt trước, rẻ) — cảnh
thuần bối cảnh không nhân vật thì `t2v`.

**Đạo cụ BIẾN THIÊN không bake vào `desc` (bài học ranh giới anchor↔cốt truyện):** `characters[].desc`
(và anchor) chỉ giữ cái **BẤT BIẾN** — mặt, tóc, trang phục khoá. Vật thể/đạo cụ **thay đổi theo mạch**
(vd hạt giống → nảy mầm; cầm đồ vật rồi đặt xuống) phải khai báo **per-scene trong `action`**, KHÔNG nhét
vào `desc`. Bake đạo cụ biến thiên vào desc/anchor → compiler lặp nó MỌI cảnh → hình ra sai (mầm hiện
trước khi nở, phá payoff bất ngờ). Cần "không có X" ở vài cảnh thì ghi phủ định trong `action` ("a round
seed, NOT a sprout, no leaves").

**Prompt ẢNH ≠ prompt CLIP (bài học `dialogue[]`→bong bóng chữ):** compiler nhét `the character says "…"`
vào `prompt` để Veo diễn khẩu hình — nhưng `scene-images` (T2I) dùng CHUNG prompt đó nên AI **vẽ speech
bubble chữ** trong ảnh. Cảnh có `dialogue[]` → sau compile, **bỏ cụm `the character says "…"` khỏi
`prompt` + set `prompt_override:true`** (giữ khẩu hình qua `action` "whispering"). Ảnh sạch, clip vẫn dub.

**Cảnh có thoại nhân vật (đa giọng):** điền `dialogue[]` (`{char, line}`) + gán `characters[].voice_id`
cho nhân vật đó. **Mô hình P1: cảnh có `dialogue[]` thì để trống `vo`** (mỗi cảnh 1 kiểu tiếng); đan
xen kể–thoại thì tách cảnh. Consumer tự kích hoạt đường đa giọng khi thấy `dialogue[]`. Chi tiết:
mục "Đa giọng" ở `references/project-schema.md`.

**Cách viết mới — điền FIELD, KHÔNG viết prompt tay** (Mức 4): `prompt` là field DẪN XUẤT do
compiler ghép. Mỗi cảnh điền:
- `action` (hành động chính, **tiếng Anh** — nội dung compiler không tự bịa), `emotion` (cảm xúc
  chủ đạo → auto-fill góc máy/ánh sáng/atmosphere theo `references/emotion-recipe.md`).
- `shot_size` (**đa dạng cỡ cảnh** giữa các cảnh liền kề), `camera_angle`, `camera_move`, `lighting`,
  `atmosphere`, `lens`, `sfx[]`, `dialogue[]` — cái nào để trống mà có `emotion` thì compiler tự điền.
- Continuity: `location` (khoá bối cảnh), `screen_direction` (giữ mạch hướng), `match_cut_with`.
- `role` (hook/setup/turn/payoff/cta), `transition` theo CẢM XÚC (dissolve vào mơ, fadewhite tỉnh
  giấc, fade đoạn dịu, cut nhịp nhanh — bảng trong schema), đừng đồng loạt 1 kiểu.

Rồi **ghép prompt tự động**:
```bash
PY=~/.venv/claude/bin/python; GEN=.agents/skills/vidgen-clips/scripts/flowgen.py
$PY $GEN compile-prompts --project projects/<tên> --dry-run   # xem trước, chưa ghi
$PY $GEN compile-prompts --project projects/<tên>             # ghi scenes[].prompt
```
Muốn viết prompt tay 1 cảnh → set `prompt_override: true` rồi ghi `prompt` (compiler bỏ qua cảnh đó).
Cảnh báo "THIẾU LIỆU" = cảnh chưa có `action` lẫn `prompt` → bổ sung. Công thức 5 khối + vựng từ
điện ảnh + continuity: `../vidgen-clips/references/veo-prompt-craft.md`.

## Bước 4 · Tự-QC rồi trình GATE 1 (script lock)

Tự kiểm trước khi trình user (gate 1 — đã nhồi craft). **Chạy `compile-prompts` xong mới QC prompt:**
☐ **hook** rõ trong 3s (short) / 30s (long), có open loop ☐ cấu trúc mạch rõ (3 hồi / kishōtenketsu)
☐ mỗi cảnh 1 ý, VO khớp ~duration ☐ prompt (đã compile) đủ 5 khối, style lặp nguyên văn, không cảnh "THIẾU LIỆU"
☐ đặc điểm nhân vật nhắc lại trong prompt ☐ **đa dạng cỡ cảnh** (shot_size không đơn điệu)
☐ **continuity**: screen_direction nhất quán mạch, cảnh cùng bối cảnh trỏ đúng `location`
☐ không yêu cầu chữ trong hình ☐ không em-dash ☐ tổng thời lượng khớp brief ☐ **1 CTA** duy nhất.
**Craft LỜI (đọc-to, theo `vo-writing-craft.md`):** ☐ câu VO đầu không dạo đầu (niên đại/tên/chào)
☐ có ≥1 open loop cấy sớm–đóng ở payoff ☐ đọc to 3 cảnh liền không đều nhịp (có câu cụt để đấm)
☐ không tính từ cảm xúc tổng kết thay được bằng chi tiết ☐ có ≥1 cảnh lặng chủ động sau beat nặng
☐ through-line 1 câu, turn+payoff cùng trục ☐ (nếu có thoại) cảnh thoại lệch khỏi close-up chính diện,
mỗi nhân vật có `voice_id`, `vo` trống ở cảnh `dialogue[]`.
Trình user duyệt kịch bản + storyboard. User gật → set `gates.script_lock = true`. **Chưa gật thì KHÔNG gen gì cả.**

## Chạy lại / sửa

Đã có `project.json` mà user muốn sửa → chỉ sửa **field craft** cảnh liên quan rồi chạy lại
`compile-prompts` (idempotent, ghi đè prompt cảnh không `prompt_override`). Cảnh đã có clip `done`
mà đổi field/`vo` thì reset `image.approved=false`, `clip.status="pending"` để stage sau gen lại đúng chỗ.
Dự án Mức 3 cũ (prompt viết tay, chưa có field) vẫn chạy y nguyên — compiler giữ prompt cũ, không xoá.
