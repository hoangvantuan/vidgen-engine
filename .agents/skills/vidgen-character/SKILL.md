---
name: vidgen-character
description: STAGE 2 của pipeline vidgen — tạo NHÂN VẬT + BỐI CẢNH NHẤT QUÁN cho video AI: char sheet → ảnh anchor (T2I flow-agent, miễn phí) → location anchor (khoá bối cảnh, Grid Method 3×3) → upload lấy media_id → gen 1 clip thử → GATE character lock. Dùng khi cần "tạo nhân vật cho video", "anchor nhân vật", "char sheet", "khoá bối cảnh", "nhân vật/bối cảnh bị đổi giữa các cảnh", "giữ nhân vật giống nhau", hoặc khi vidgen-flow gọi STEP 2.
---

# Vidgen Character (char sheet → anchor → character lock)

Nguyên lý (chi tiết + bằng chứng: `references/consistency-and-ai-tells.md`): **char sheet cho
NGƯỜI duyệt danh tính, anchor cho MÁY bám theo**. Nạp nhầm char sheet vào Flow → AI tưởng đám
đông, trộn mặt. Giữ nhất quán bằng **ẢNH-anchor (đã verify nguồn chính thức Google), KHÔNG bằng
mô tả chữ hay seed** (lối "tả chi tiết = nhất quán" đã bị bác). Ảnh T2I miễn phí — gen tới khi ưng.

```bash
PY=~/.venv/claude/bin/python
GEN=.agents/skills/vidgen-clips/scripts/flowgen.py   # engine dùng chung
```

## Bước 1 · MASTER DESIGN SHEET (cho người duyệt — bản thể hiện thị giác của bảng element)

Mỗi nhân vật CHÍNH → gen 1 **master design sheet** bằng T2I — 1 lần render nên mọi biến thể
cùng ánh sáng/style/tỉ lệ (ưu điểm cốt lõi của sheet). Nội dung chuẩn (theo mẫu đã chốt 07-12):
**turnaround đủ góc** (front · 3/4-front trái/phải · trái · phải · lưng) + **expressions** (6-8
biểu cảm) + **poses** đặc trưng + **accessories/hero-prop** + **color palette** + **companion**
(nhân vật phụ đi kèm nếu có) + **close-up chi tiết** (mắt, hoạ tiết áo):
```bash
$PY $GEN t2i --prompt "character design sheet for <tên>, <desc EN>: full turnaround (front, \
3/4 front left, 3/4 front right, left side, right side, back), 6 facial expressions, key poses, \
accessories laid out separately, color palette swatches, close-up details, consistent outfit \
and lighting across all views, plain background, <style chung của dự án>" \
  --aspect landscape --out projects/<tên>/02_characters/<id>_sheet.png
```
User duyệt danh tính (mặt, trang phục, palette, vibe) TRÊN SHEET trước — sửa ở đây rẻ nhất; sheet
đã duyệt = nguồn sự thật thị giác cho GATE 1A2 (elements.md trỏ tới) và chuẩn so chéo ở GATE 2.
**Sheet TUYỆT ĐỐI không nạp vào Flow làm reference** (nhiều hình/ảnh → Veo trộn mặt, verify 3-0);
expressions/poses cũng KHÔNG anchor hoá — biểu cảm là việc của `emotion`/`action` per shot.

## Bước 2 · Anchor (cho máy)

**MỌI nhân vật xuất hiện mặt-rõ (medium trở gần) hoặc lặp ≥2 cảnh đều phải có entry + anchor —
KHÔNG phân biệt chính/phụ.** Bài học đo được (bé Tuệ An): mẹ/bà cụ/các em chỉ là chữ trong action
→ mỗi generation Veo bịa một người khác — chính là nguồn "chi tiết lệch" lớn nhất. `flowgen
qc-storyboard` (nhóm THỰC THỂ) bắt nhân vật mồ côi; đám đông/người nền thì KHÔNG anchor, viết
action né mặt (turned away / silhouette / out of focus).

Nhân vật CHÍNH → **ĐỦ GÓC theo turnaround của master sheet** (front · 3q_front_left ·
3q_front_right · left · right · back — nhất quán với luật location 9 góc, mandate chất lượng:
shot đổi góc mà thiếu anchor góc đó là Veo tự bịa). Nhân vật phụ ít cảnh → tối thiểu front + side.
Gen TỪNG anchor riêng (KHÔNG cắt từ sheet — độ phân giải ô sheet thấp), dùng ảnh hero/sheet đã
duyệt làm `--ref` để anchor bám đúng thiết kế:
```bash
$PY $GEN t2i --prompt "<desc EN>, front view, standing, plain white background, \
full body, single character, <style chung>" --aspect portrait \
  --ref <media_id ảnh hero đã upload> \
  --out projects/<tên>/02_characters/<id>_front.png
```
Đặt `angle` đúng tên góc (front/3q_front_left/.../back) — flowgen `_pick_anchor` chọn anchor
khớp `angle` của shot.
Yêu cầu anchor: **1 người/ảnh · 1 góc · nền trơn · rõ mặt · style đồng bộ giữa mọi anchor**.
Lệnh in ra `media_id` → ghi ngay vào `characters[].anchors[]` trong manifest.
Ảnh có sẵn (user đưa) thì upload: `$PY $GEN upload-image path.png` → lấy media_id.
**Đồng bộ ngược `desc` theo anchor:** nếu anchor sinh chi tiết ngoài `desc` (vd ông cầm gậy tre)
mà bạn muốn giữ → **cập nhật `characters[].desc` cho khớp anchor**. Desc là nguồn sự thật đưa vào
prompt mọi cảnh; lệch anchor sẽ làm các cảnh sau mâu thuẫn với nhân vật.

## Bước 2b · Location anchor — KHOÁ BỐI CẢNH (chống "mỗi cảnh một kiểu quán")

Nhân vật giữ mặt nhờ anchor; **bối cảnh cũng cần anchor** — nếu không, cùng "quán cà phê" mỗi cảnh
Veo vẽ một kiểu (đổi cửa sổ, đổi bàn ghế, đổi ánh sáng). Với mỗi `locations[]` trong manifest:

**Grid Method 3×3 (nguồn: CinematicHubClone) — gen NHIỀU góc bối cảnh trong 1 lần render**, nên
cùng ánh sáng/chi tiết → đồng nhất tuyệt đối, lại rẻ (1 credit thay vì 9). Dùng làm sheet duyệt:
```bash
$PY $GEN t2i --prompt "3x3 grid of 9 frames of THE SAME location from different angles \
(wide, corner, over-the-shoulder, low, high...), <location desc EN>, no people, \
consistent lighting and props across all 9 frames, <style chung>" \
  --aspect landscape --out projects/<tên>/02_locations/<id>_grid.png
```
Rồi gen **từng location anchor riêng** (KHÔNG người, style chung) để lấy media_id cho máy bám —
**ĐỦ 9 GÓC theo grid ngay từ đầu** (wide/corner/reverse/left/right/high/low/detail/entrance —
bám sát 9 ô của grid đã duyệt, mỗi góc 1 lệnh t2i, đặt `angle` đúng tên góc):
```bash
$PY $GEN t2i --prompt "<location desc EN>, wide establishing view, no people, \
consistent props, <style chung>" --aspect landscape \
  --out projects/<tên>/02_locations/<id>_wide.png
```
Yêu cầu location anchor: **KHÔNG có người · nền/bối cảnh đầy đủ · style + ánh sáng đồng bộ**.
Vì sao đủ 9 từ đầu (đã chốt, mandate chất-lượng-trước-credit): cảnh dùng góc THIẾU anchor →
Veo tự bịa layout từ chữ → nhà cửa/hàng cây mỗi cảnh một kiểu; ảnh miễn phí, chỉ tốn công duyệt.

## Bước 2c · Hero-prop anchor — KHOÁ ĐẠO CỤ (props[] registry)

Đạo cụ lặp ≥2 cảnh phải có entry trong `props[]` (desc chuẩn — compiler lặp nguyên văn, hết
"mỗi cảnh tả bát cháo một kiểu"). Trong đó **hero-prop** (gần camera / mang nghĩa truyện, vd củ
khoai) PHẢI có ảnh anchor:
```bash
$PY $GEN t2i --prompt "<prop desc EN>, product still, plain neutral background, \
single object, <style chung>" --aspect square --out projects/<tên>/02_props/<id>.png
```
Ghi `media_id` vào `props[].anchor`. Prop GẮN BỐI CẢNH (nồi trên bếp, chum nước) → đừng anchor
riêng, **BAKE thẳng vào ảnh location anchor** (Veo neo theo, không tốn slot ref).
> **Neo TỈ LỆ tại đây:** scale vật-với-vật dựng trong location anchor (vd cây khổng lồ cạnh
> người) được Veo **bảo toàn qua mọi cảnh**. Muốn tỉ lệ lệch-thực NHẤT QUÁN theo style archetype
> (`vidgen-clips/references/veo-prompt-craft.md` mục 2b) → bake sẵn vào anchor, đừng chỉ dựa prompt keyword (dễ trôi).
Ghi `media_id` vào `locations[].anchors[]`. Cảnh trỏ `scenes[].location: "<id>"` → flowgen dùng
location anchor + character anchor cùng lúc làm ref (tổng ≤ 3 ref/prompt), compiler lặp nguyên văn
`desc` bối cảnh vào `[Context]`.
> **Scene-as-asset** (CinematicHubClone): gom tối đa hành động vào CÙNG một location để đỡ vỡ
> consistency; đổi location thì chuyển qua yếu tố môi trường (mây → mây phủ rừng), đừng nhảy đột ngột.

## Bước 3 · Clip thử (đốt credit NHỎ trước khi đốt LỚN)

**Nguyên lý — clip thử là PHÉP THĂM DÒ NĂNG LỰC engine ở tầng đắt nhất, KHÔNG phải "cảnh đại diện trung bình".**
Ranh giới ảnh→video có giả định ngầm nguy hiểm: *"ảnh T2I gen được thì clip I2V cũng gen được"* — **SAI**.
Veo có safety/giới hạn riêng ở tầng VIDEO mà tầng ảnh không lộ (đã gặp: clip trẻ em + đói bị chặn
`MEDIA_GENERATION_STATUS_FAILED` dù ảnh gen bình thường). Vì vậy **chọn cảnh RỦI RO CAO NHẤT của dự án
làm clip thử** — nội dung nhạy cảm nhất (trẻ em/bạo lực/đau khổ/y tế) hoặc tương tác/chuyển động phức tạp nhất.
Cảnh khó nhất qua được thì phần còn lại gần như chắc qua; nó chặn thì biết NGAY (1 credit) thay vì vỡ giữa
batch (chục credit). Đừng chọn cảnh phong cảnh/tĩnh cho "chắc ăn" — chắc ăn kiểu đó là tự lừa.
**Dự án có cảnh coverage (`shots[]`, timestamp prompting):** clip thử NÊN là (hoặc kèm) MỘT cảnh
coverage — đã kiểm chứng nội bộ 1 mẫu nhưng 1 mẫu ≠ khái quát, mỗi dự án vẫn đo thật TRƯỚC khi cả
batch đặt cược vào nó. Soi: có cắt đúng mốc không? các cú có giữ nhân vật/ánh sáng nội tại không?
Không đạt → hạ cảnh đó về 1 cú hoặc chuyển đường master→regen (`scene-grammar.md §6b`).
**Dự án có cảnh composite (`composite:true`, cảnh đông thực thể):** clip thử PHẢI kèm 1 cảnh đi
đường `compose-frame` → i2v — đường composite CHƯA kiểm chứng thật trên engine này; soi khung
composite giữ đúng mặt TỪNG nhân vật (không trộn), rồi clip i2v có giữ tiếp không.
**Dự án shot-first (workflow v2 — mặc định dự án mới):** clip thử PHẢI kèm 1 cảnh ≥2 shot đi trọn
đường **master → derive → stitch** — kỹ thuật derive (ảnh shot con ref frame master) CHƯA kiểm
chứng thật; soi: shot con giữ đúng không gian/ánh sáng master? mặt vẫn khớp anchor gốc? bản stitch
cắt nội cảnh có mượt không?

Gen thử cảnh rủi ro nhất có nhân vật:
```bash
$PY $GEN scene-images --project projects/<tên> --scene <id>   # ảnh khung đầu, miễn phí
# user ưng ảnh → set image.approved=true → gen thử 1 clip:
$PY $GEN scene-clips --project projects/<tên> --scene <id> --force
```
Soi clip thử: nhân vật giống anchor? style đúng? chuyển động tự nhiên? AI-tell (thừa ngón,
mặt biến dạng)?

## Bước 4 · GATE 2 (character lock)

Trình user: char sheet + anchors + clip thử. **Tự-QC craft trước khi trình** (xem
`references/consistency-and-ai-tells.md`) — chạy checklist ở góc *tìm lỗi*, rồi nêu thẳng
điểm yếu còn lại thay vì xin gật (phản biện gate: `../vidgen-script/references/decision-grilling.md`),
vd "frame nào của clip thử LỆCH anchor nhất — chấp nhận được không?":
☐ anchor 1-người/1-góc/nền trơn/rõ mặt ☐ clip thử giữ mặt khớp anchor qua các frame
☐ không AI-tell (thừa ngón, méo mặt, morphing) ☐ style đồng bộ giữa mọi anchor.
☐ **tỉ lệ vật-với-vật khớp style archetype?** (tả thực = đúng đời thực; cách điệu = lệch có chủ đích, không phải lỗi).
☐ **duyệt anchor theo LÔ — so CHÉO style toàn bộ:** bày MỌI anchor cạnh nhau (nhân vật ×N góc +
location ×9 + hero-prop) trong 1 lượt xem; 1 anchor lệch style (màu, nét vẽ, ánh sáng) = mọi cảnh
dùng nó lệch theo — **lỗi nhân bản từ gốc, phải bắt TRƯỚC khi lock**, gen lại anchor lệch (miễn phí).
User gật → set `gates.character_lock = true`.
Từ đây **danh tính nhân vật KHÓA** — không đổi desc/anchor giữa chừng; đổi = gen lại từ đầu.

## Chạy lại / sửa

User chê nhân vật sau khi đã lock → cảnh nào đã gen với anchor cũ phải reset
(`image.approved=false`, `clip.status="pending"`), báo rõ chi phí gen lại trước khi làm.
