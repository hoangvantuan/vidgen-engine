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

### 🚦 GATE 1A · Story lock — DUYỆT KỊCH BẢN trước khi dựng storyboard (CHẶN CỨNG)

**Kịch bản ràng buộc mọi bước sau (anchor/prompt/gen clip/ráp) → chốt HƯỚNG ở tầng lời rẻ nhất, TRƯỚC
khi đổ công vào field/compile.** Chạy **Cây phản biện kịch bản** trong `references/decision-grilling.md`:
tự soi 5 trục ở góc *tìm lỗi*, nêu 1-2 điểm yếu chưa chắc, rồi trình user bản **lời VO đọc-to** (chỉ
`kichban.md`, CHƯA kèm storyboard/prompt):
☐ **through-line** 1 câu, `turn`+`payoff` cùng trục ☐ có **≥1 open loop** cấy sớm–đóng payoff
☐ mạch không cảnh thừa / không gãy ☐ **hook** không dạo đầu, gợi tò mò 3s(short)/30s(long)
☐ **đọc to** 3 cảnh liền: không vấp, không đều nhịp, không tính từ cảm xúc tổng kết.
User gật → set `gates.story_lock = true`. **Chưa gật thì KHÔNG sang Bước 2b (element pass).**
Đổi hướng ở đây một câu; đổi sau khi compile phải chạy lại cả stage.

## Bước 2b · ELEMENT PASS — tách bảng element từ kịch bản (workflow v2)

> **Điều kiện vào:** `gates.story_lock = true`. Mục đích: nhìn TOÀN BỘ dàn element MỘT LƯỢT
> trước khi rải vào N cảnh — bệnh nhân-vật-mồ-côi sinh từ chỗ thiếu bảng kiểm này.

Đọc kịch bản đã duyệt, TÁCH mọi thực thể xuất hiện thành bảng, ghi 2 nơi:
1. **`project.json`**: điền `characters[]` (MỌI nhân vật mặt-rõ/lặp ≥2 cảnh, kể cả vai phụ) +
   `props[]` (đạo cụ lặp, hero-prop đánh dấu) + `locations[]` + `music.ambience`.
2. **`01_script/elements.md`** (bản cho người duyệt): bảng
   `| id | loại | desc | cách khoá | xuất hiện ở cảnh |` — cách khoá ∈ {anchor riêng · registry
   desc · bake vào location anchor · né mặt (đám đông)}.

### 🚦 GATE 1A2 · Element lock — DUYỆT BẢNG ELEMENT trước khi dựng storyboard (CHẶN CỨNG)

Trình `elements.md`, tự soi trước: ☐ không sót ai/vật nào kịch bản nhắc tới ☐ mỗi element có
cách khoá rõ ☐ prop gắn bối cảnh đã chuyển sang "bake vào location" ☐ đám đông có ghi chú né mặt.
User gật → `gates.element_lock = true`. Storyboard (Bước 3) chỉ được TRỎ id từ bảng này —
compile chặn khi gate chưa mở, QC bắt id lạ.

## Bước 3 · Storyboard máy-đọc-được (SHOT-FIRST — điền FIELD → compiler ghép prompt per shot)

> **Điều kiện vào:** `gates.story_lock = true` VÀ `gates.element_lock = true`.

**Workflow v2 — SHOT là đơn vị sản xuất, SCENE là container ngữ nghĩa** (beat + location + state
+ VO): mỗi cảnh khai `shots[]` kiểu **separate** (mỗi shot có `duration` + `shot_size` + `action`
riêng → gen/duyệt/regen ĐỘC LẬP từng shot; xem 2 style trong `project-schema.md`). Luật:
- Cảnh 1 ý đơn giản / cảnh ngấm = **1 shot** (long-take 8-10s, đừng băm).
- Cảnh ≥2 shot: shot ĐẦU là **MASTER** (wide/establishing thiết lập không gian) — shot con
  (close/insert/reaction) derive từ master khi gen. Tổng duration shot ≈ duration cảnh (khớp VO).
- VO/dialogue/state/transition vẫn ở cấp SCENE; cine + action ở cấp SHOT.

Tạo `projects/<tên>/project.json` theo schema — **đọc `references/project-schema.md` VÀ
`references/scene-grammar.md` trước khi viết file này** (schema: quy tắc field, VO khớp duration,
cơ chế compiler; scene-grammar: ngữ pháp cảnh — coverage, tiến trình cỡ cảnh, 5 luật continuity,
nhịp dựng, quy tắc kích hoạt link_prev/match_cut/re-establish cho TỪNG cặp cảnh liền kề).
Điền: `characters` (desc chi tiết; **`voice_id` nếu nhân vật có thoại** — xem dưới), `locations`
(nếu khoá bối cảnh), `props[]` registry, `style` chung, scenes. Mặc định `mode: "i2v"` (ảnh duyệt
trước, rẻ) — cảnh thuần bối cảnh không nhân vật thì `t2v`.

**Luật đồng bộ thực thể (mandate chất lượng — nguồn lệch lớn nhất đã đo được):**
- **MỌI nhân vật mặt-rõ hoặc lặp ≥2 cảnh → entry `characters[]`** (kể cả vai phụ: mẹ, bà cụ, em
  bé). Không entry = mỗi generation một khuôn mặt khác. Đám đông/người nền → action né mặt
  (turned away / silhouette / out of focus), KHÔNG entry.
- **Đạo cụ lặp ≥2 cảnh → entry `props[]`** (desc chuẩn duy nhất; hero-prop đánh `hero:true` để
  stage 2 gen anchor). Cảnh dùng prop → khai `scenes[].props: [id]`.
- **Cảnh ĐÔNG (>3 ứng viên neo: nhân vật + hero-prop + location) → `composite: true`** — đi đường
  compose-frame (ghép dần từng thực thể vào khung đầu, không vướng giới hạn 3 ref). QC tự đếm và WARN.
- **`state{}` per cảnh — SỔ LIÊN TỤC (script supervisor):** `time_of_day`/`weather` (trống = kế
  thừa cảnh trước), `wardrobe`/`condition` per nhân vật (chỉ cái NHÌN THẤY: quần áo bẩn dần, mặt
  hốc hác dần), `held_props` (ai cầm gì), `position` (metadata cho QC soi teleport). Claude điền
  khi dựng storyboard — trạng thái phải TIẾN TRIỂN hợp lý một chiều theo mạch (đói dần, không hồi
  phục vô cớ); QC đo thời-gian-chạy-lùi và lighting mâu thuẫn time_of_day.

**Đạo cụ BIẾN THIÊN không bake vào `desc` (bài học ranh giới anchor↔cốt truyện):** `characters[].desc`
(và anchor) chỉ giữ cái **BẤT BIẾN** — mặt, tóc, trang phục khoá. Vật thể/đạo cụ **thay đổi theo mạch**
(vd hạt giống → nảy mầm; cầm đồ vật rồi đặt xuống) phải khai báo **per-scene trong `action`**, KHÔNG nhét
vào `desc`. Bake đạo cụ biến thiên vào desc/anchor → compiler lặp nó MỌI cảnh → hình ra sai (mầm hiện
trước khi nở, phá payoff bất ngờ). Cần "không có X" ở vài cảnh thì ghi phủ định trong `action` ("a round
seed, NOT a sprout, no leaves").

**Bong bóng thoại (bài học `dialogue[]` — ĐÃ FIX TẠI NGUỒN):** compiler KHÔNG còn nhét câu thoại
literal vào prompt (chữ trong prompt → AI vẽ speech bubble); cảnh có `dialogue[]` chỉ được phát
tín hiệu trung tính "speaking warmly, mouth gently open" cho khẩu hình động, lời thật do TTS đọc.
NO_TEXT cũng đã kèm "no speech bubbles". Không cần bước tay bỏ cụm thoại + prompt_override nữa.

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
- `role` (hook/setup/turn/payoff/cta), `transition`: **mặc định `cut`** — transition mềm là dấu câu
  mang nghĩa (dissolve vào mơ, fadewhite tỉnh giấc, fade thời gian trôi), mỗi lần dùng phải nói được
  nghĩa; fade đồng loạt = trôi đều slideshow (bài học đo được 67%).
- `duration` **biến thiên theo beat** (bài học 15/15 cảnh đúng 8s = slideshow): căng/hành động 4-6s,
  ngấm cảm xúc/lặng 8-10s, leo thang cao trào NGẮN DẦN. VO viết khớp (~3-4 chữ/giây).
- **Coverage cho beat ĐẮT (`shots[]` separate):** cảnh `role: hook/turn/payoff` và cảnh
  `dialogue[]` → kể bằng 2-3 shot riêng (master wide + cận/insert/reaction, mỗi shot
  `duration/shot_size/action`); biến thể tiết kiệm: timestamp `from/to` trong 1 generation
  (đã kiểm chứng 1 mẫu) khi chấp nhận không regen lẻ từng cú.
  Cảnh ngấm cần cú dài thì ĐỪNG dùng. Đi qua **bảng kích hoạt continuity** (`scene-grammar.md §7`)
  cho TỪNG cặp cảnh liền kề — giờ là BẮT BUỘC điền khi khớp bảng, không phải gợi ý (bài học 0/15
  dùng dù field có sẵn): liên tục thời-không → `link_prev`; **cắt đổi góc CÙNG không gian (mode
  r2v) → `ref_prev`** (frame cảnh trước thay location anchor — giữ ánh sáng/layout);
  cùng sự kiện đổi cỡ → `match_cut_with`; vào location mới → mở wide/establishing (re-establish).

Rồi **ghép prompt tự động**:
```bash
PY=~/.venv/claude/bin/python; GEN=.agents/skills/vidgen-clips/scripts/flowgen.py
$PY $GEN compile-prompts --project projects/<tên> --dry-run   # xem trước, chưa ghi
$PY $GEN compile-prompts --project projects/<tên>             # ghi scenes[].prompt
```
Muốn viết prompt tay 1 cảnh → set `prompt_override: true` rồi ghi `prompt` (compiler bỏ qua cảnh đó).
Cảnh báo "THIẾU LIỆU" = cảnh chưa có `action` lẫn `prompt` → bổ sung. Công thức 5 khối + vựng từ
điện ảnh + continuity: `../vidgen-clips/references/veo-prompt-craft.md`.

## Bước 4 · Tự-QC rồi trình 🚦 GATE 1B (script lock — storyboard/prompt)

> Kịch bản đã qua GATE 1A; gate này duyệt **KỸ THUẬT** (field/prompt/cỡ cảnh/continuity), không bàn
> lại hướng. Nếu QC phát hiện phải đổi HƯỚNG kịch bản → quay lại Bước 2 + mở lại `story_lock=false`.

Tự kiểm trước khi trình user (GATE 1B — đã nhồi craft). **Chạy `compile-prompts` xong, chạy tiếp
QC máy đo rồi mới soi tay** (máy đo cái đo được — nhịp/góc/transition/continuity; người quyết):
```bash
$PY $GEN qc-storyboard --project projects/<tên>   # warn-only; mỗi ⚠ hoặc sửa hoặc nêu lý do phá cách
```
☐ **hook** rõ trong 3s (short) / 30s (long), có open loop ☐ cấu trúc mạch rõ (3 hồi / kishōtenketsu)
☐ mỗi cảnh 1 ý, VO khớp ~duration ☐ prompt (đã compile) đủ 5 khối, style lặp nguyên văn, không cảnh "THIẾU LIỆU"
☐ đặc điểm nhân vật nhắc lại trong prompt ☐ **đa dạng cỡ cảnh VÀ góc máy** (shot_size, camera_angle
không đơn điệu — chuỗi ≥3 cảnh trùng góc phải có lý do trục điểm nhìn ghi trong kichban.md)
☐ **nhịp**: duration biến thiên theo beat, không chuỗi ≥4 cảnh cùng độ dài vô cớ ☐ transition mặc định
cut, mỗi fade/dissolve nêu được nghĩa ☐ **beat đắt (hook/turn/payoff/thoại) có coverage `shots[]`**
hoặc lý do 1 cú ☐ **continuity**: screen_direction nhất quán mạch, cảnh cùng bối cảnh trỏ đúng
`location`, vào location mới có re-establish, cặp cảnh liền kề đã qua bảng kích hoạt (`scene-grammar.md §7`)
☐ không yêu cầu chữ trong hình ☐ không em-dash ☐ tổng thời lượng khớp brief ☐ **1 CTA** duy nhất.
**Đồng bộ thực thể + sổ liên tục (nhóm THỰC THỂ/STATE của QC):** ☐ không nhân vật mồ côi (mọi ⚠
"action nhắc người" đã xử: thêm entry hoặc né mặt) ☐ prop lặp có registry, hero-prop đánh dấu
☐ cảnh >3 ứng viên neo có `composite:true` ☐ state điền đủ các cảnh có nhân vật, trạng thái tiến
triển 1 chiều hợp mạch (đói dần/bẩn dần — soi NGỮ NGHĨA bằng mắt, máy chỉ đo time/lighting)
☐ không teleport: cặp cảnh liền kề đổi location xa phải có ellipsis hợp lý trong VO/action.
**Craft LỜI (đọc-to, theo `vo-writing-craft.md`):** ☐ câu VO đầu không dạo đầu (niên đại/tên/chào)
☐ có ≥1 open loop cấy sớm–đóng ở payoff ☐ đọc to 3 cảnh liền không đều nhịp (có câu cụt để đấm)
☐ không tính từ cảm xúc tổng kết thay được bằng chi tiết ☐ có ≥1 cảnh lặng chủ động sau beat nặng
☐ through-line 1 câu, turn+payoff cùng trục ☐ (nếu có thoại) cảnh thoại lệch khỏi close-up chính diện,
mỗi nhân vật có `voice_id`, `vo` trống ở cảnh `dialogue[]`.
Trình user duyệt storyboard. User gật → set `gates.script_lock = true`. **Chưa gật thì KHÔNG gen gì cả.**

## Chạy lại / sửa

Đã có `project.json` mà user muốn sửa → phân biệt **sửa HƯỚNG** (through-line/mạch/lời VO) vs **sửa
KỸ THUẬT** (field/prompt). Sửa hướng → set lại `gates.story_lock=false`, quay về Bước 2, duyệt lại GATE
1A rồi mới compile. Sửa kỹ thuật → chỉ sửa **field craft** cảnh liên quan rồi chạy lại
`compile-prompts` (idempotent, ghi đè prompt cảnh không `prompt_override`). Cảnh đã có clip `done`
mà đổi field/`vo` thì reset `image.approved=false`, `clip.status="pending"` để stage sau gen lại đúng chỗ.
Dự án Mức 3 cũ (prompt viết tay, chưa có field) vẫn chạy y nguyên — compiler giữ prompt cũ, không xoá.
