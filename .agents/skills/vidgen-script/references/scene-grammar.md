# Ngữ pháp cảnh — découpage & nhịp dựng cho video AI (Stage 1 · vidgen-script · Bước 3)

Vì sao video AI hay "phẳng như trình chiếu ảnh động": mỗi beat được kể bằng **một cú máy rời**,
nhịp cắt đều tăm tắp, không có shot phụ dẫn mắt. File này là quy ước **thiết kế cảnh** (découpage)
khi dựng storyboard — bổ cho `hook-and-structure.md` (cấu trúc MẠCH) và `vo-writing-craft.md` (con
CHỮ): cùng một kịch bản, cách chia cú máy quyết định nó xem như phim hay như slideshow.

> **Chánh kiến:** toàn bộ là quy ước craft dựng phim cổ điển (ổn định hơn 80 năm) + kỹ thuật Veo/Flow
> có nguồn chính thức. KHÔNG có số % retention nào ở đây. Bằng chứng nội bộ: dự án thật đầu tiên
> (bé Tuệ An) đo được 15/15 cảnh đúng 8.0s, 60% high-angle (8 cảnh mở đầu LIÊN TIẾP cùng góc),
> 0/15 dùng match_cut/link_prev, 67% fade — tất cả đều là luật dưới đây bị bỏ trống.

---

## 1 · Scene ≠ Shot — và map vào pipeline

| Khái niệm | Định nghĩa | Trong pipeline |
|---|---|---|
| **Shot** (cú máy) | 1 đoạn quay liên tục không cắt | 1 clip gen, HOẶC 1 phần tử `shots[]` trong cảnh |
| **Scene** (cảnh kịch) | hành động liên tục tại 1 địa điểm, 1 mốc thời gian | 1 phần tử `scenes[]` (beat của mạch kể) |

Phim thật: 1 scene được **cover bằng nhiều shot** — vì mắt khán giả cần được DẪN (nhìn đúng chỗ),
thời gian cần được NÉN (cắt bỏ phần thừa), cảm xúc cần KHOẢNG CÁCH thay đổi (cỡ cảnh = khoảng cách
tâm lý). Một cú máy dài cố định làm cả ba việc đều tệ — và với AI còn tệ hơn: cú càng dài, model
càng có thời gian morph/trôi (chất lượng AI đạt đỉnh ở 4-6 giây đầu của một generation).

**Mô hình pipeline (hybrid 2 tầng):** mặc định 1 cảnh = 1 cú như cũ (rẻ, đủ cho cảnh chuyển tiếp,
b-roll, cảnh ngấm cần cú dài). Beat ĐẮT — `role: hook | turn | payoff` và cảnh có `dialogue[]` —
cân nhắc **coverage**: kể bằng 2-3 cú cắt xen, khai báo qua `shots[]` (xem §7).

## 2 · Coverage — bộ shot phủ một cảnh, mỗi loại một nhiệm vụ

| Loại shot | Nhiệm vụ kể chuyện |
|---|---|
| **Master / establishing** (wide) | Thiết lập KHÔNG GIAN: ai ở đâu, quan hệ vị trí. Xương sống để mọi cú khác neo vào. |
| **Medium** | Cảnh làm việc chính: thấy người + cử chỉ, vẫn đọc được mặt. |
| **Close-up** | Cảm xúc, khoảnh khắc quyết định. ĐẮT GIÁ — để dành cho beat nặng, dùng tràn lan thì mất giá. |
| **Extreme close-up** | Nhấn tối đa 1 chi tiết: ánh mắt, bàn tay run, hạt gạo cuối cùng. |
| **Insert** | Cận 1 VẬT thuộc cảnh mang thông tin cốt truyện: lá thư, bát cháo vơi, củ khoai. |
| **Cutaway** | Cắt sang thứ khác rồi quay lại: người nghe, vật ngoài khung, ký ức chớp. |
| **Reaction shot** | Mặt người ĐANG NGHE/chứng kiến. Khán giả hiểu sự kiện phần lớn qua gương mặt người chứng kiến nó, không qua bản thân sự kiện. |
| **Shot/reverse-shot** | Cú pháp chuẩn hội thoại: A nói → cắt B đáp (kèm luật 180°, §4). |
| **POV** | Máy = mắt nhân vật, đi cặp: cú nhân vật nhìn → cú POV thứ họ thấy. |

**Vì sao thiếu insert/reaction thì phẳng:** chỉ có master + medium tuần tự = khán giả xem từ xa,
không được dẫn mắt, không được "cho biết phải cảm thấy gì". Insert/cutaway còn là **băng cứu thương
của dựng AI**: chèn 1-2s cận-vật giữa 2 cú không khớp ánh sáng/nối tiếp → mắt khán giả "reset",
não chấp nhận thay đổi nhỏ mà không bắt lỗi. Đây là cách rẻ nhất để giấu chỗ ghép giữa các clip gen rời.

## 3 · Tiến trình cỡ cảnh trong một cảnh

Mặc định (quy ước vững, ĐỂ PHÁ có chủ đích chứ không phải luật cứng):
- **Vào bằng wide/establishing** khi tới KHÔNG GIAN MỚI — đặt bàn cờ trước, khán giả biết mình ở đâu.
- **Tiến gần dần khi cảm xúc leo** (wide → medium → close). Close-up là "đỉnh" của thang, dành cho
  khoảnh khắc nặng nhất của cảnh.
- **Lùi ra khi giải toả** hoặc chốt cảnh.

Phá có chủ đích (ghi chú lý do vào storyboard để GATE 1B không bắt nhầm):
- **Mở bằng close bí ẩn** → giấu không gian gây tò mò, rồi wide "tiết lộ" (hợp hook).
- **Giữ wide suốt cảnh nặng** → cảm giác lạnh lùng/bất lực (không cho khán giả lại gần).
- **Trì hoãn establishing** → mất phương hướng chủ động (kinh dị/hồi hộp).

**Điểm nhìn (camera_angle) cũng là một trục phải THIẾT KẾ, không để trôi:** góc máy mang nghĩa
(high = nhỏ bé/quan sát, low = quyền lực, eye = ngang hàng). Trùng góc 2-3 cảnh liền có thể là chủ
đích (trục "nhìn xuống thân phận"); trùng 8 cảnh liền không ai nhớ lý do = trôi. Nếu giữ 1 góc dài
hơi LÀ chủ đích → ghi 1 dòng lý do trong kichban.md; QC warn thì đối chiếu dòng đó.

## 4 · Continuity — 5 luật giữ liền mạch (vững nhất, vi phạm là khán giả "vấp")

| Luật | Nội dung | Lỗi khi vi phạm |
|---|---|---|
| **180° (line of action)** | Vẽ đường nối 2 nhân vật (hoặc hướng đi). Máy ở MỘT phía đường đó suốt cảnh: A luôn phải khung, B luôn trái. | Nhảy trục: 2 người như đổi chỗ/quay lưng nhau. |
| **Eyeline match** | Nhân vật nhìn ra ngoài khung hướng nào → cú kế (thứ họ nhìn) phải khớp hướng + cao độ ánh nhìn. | Quan hệ "ai nhìn gì" đứt gãy. |
| **Screen direction** | Hướng di chuyển giữ nhất quán qua cắt (L2R thì cảnh sau vẫn L2R). Field `screen_direction` — AI hay tự lật hướng. | Đang đi tới hoá thành quay đầu. |
| **Match on action** | Cắt ĐÚNG GIỮA một động tác, động tác chảy liền qua 2 cú khác cỡ. Field `match_cut_with` + `subject_position`. | Động tác giật/lặp, lộ điểm cắt. |
| **30°** | 2 cú liên tiếp cùng chủ thể phải lệch góc ≥30° VÀ/HOẶC đổi cỡ cảnh rõ. | Jump cut như giật hình — chỉ dùng khi CỐ Ý (nhịp gấp, nhảy thời gian). |

Ranh giới với `veo-prompt-craft.md §6`: file đó lo **viết prompt** giữ continuity (từ ngữ, lặp
nguyên văn); file này lo **thiết kế cảnh** — quyết định cú nào cần nối gì TRƯỚC khi viết prompt.

## 5 · Nhịp dựng — duration phải BIẾN THIÊN theo beat

Bằng chứng nội bộ: 15/15 cảnh đúng 8.0s là chữ ký "slideshow" rõ nhất. Nhịp chỉ có nghĩa khi
TƯƠNG PHẢN — nhanh chỉ "nhanh" khi trước đó có chậm để so.

- **Cảnh căng/hành động/liệt kê dồn** → 4-6s, VO ngắn (~3-4 chữ/giây → cảnh 4s ≈ 12-16 chữ).
- **Cảnh ngấm cảm xúc/dấu lặng/thiết lập không gian** → 8-10s, cho hình thở (khớp `vo-writing-craft §5`).
- **Leo thang tới cao trào** → duration NGẮN DẦN qua chuỗi cảnh (accelerated cutting — kỹ thuật
  cổ điển tạo climax).
- Chuỗi ≥4 cảnh liên tiếp cùng duration = cờ đỏ trừ khi chủ đích (nhịp đều thôi miên cho ru ngủ).

**Transition mặc định là `cut`.** Phim mặc định CẮT; fade/dissolve/fadewhite là dấu câu mang nghĩa
(thời gian trôi, vào mơ, tỉnh giấc) — mỗi lần dùng phải trả lời được "nghĩa gì ở đây?". Đo được
67% fade đồng loạt = dùng fade làm "keo an toàn" vô nghĩa, chính nó tạo cảm giác trôi đều đều.

**Rule of Six (Walter Murch) — thang ưu tiên khi các luật XUNG ĐỘT nhau:**
cảm xúc (51%) > câu chuyện (23%) > nhịp (10%) > eye-trace (7%) > mặt phẳng 2D (5%) > không gian 3D (4%).
Số là THANG Murch tự đặt trong sách (không phải đo khán giả) — ý nghĩa: khi buộc phải chọn, hy sinh
từ dưới lên — bỏ continuity không gian trước, giữ cảm xúc bằng mọi giá. Cắt đúng cảm xúc mà lệch
trục 180° vẫn hơn cắt đúng trục mà chết cảm xúc.

## 6 · Coverage trên Veo/Flow — 3 đường, chọn theo giá

### 6a · Timestamp prompting (đường CHÍNH — 0 credit thêm) [nguồn chính thức Google Cloud]

Veo 3.1 nhận prompt đánh MỐC THỜI GIAN để gen NHIỀU cú cắt xen trong CÙNG 1 generation:

```
[00:00-00:03] Wide shot: an old woman presses a sweet potato into a small girl's hands, village road at dusk.
[00:03-00:06] Close-up on the girl's face, eyes widening, she looks up at the woman.
[00:06-00:08] Insert: the sweet potato in the girl's small hands, still warm, steam rising.
```

- Các cú nằm chung 1 lần gen → nhất quán NỘI TẠI cao nhất (cùng nhân vật, cùng ánh sáng, cùng
  không gian) — giải đúng chỗ khó nhất của coverage bằng regen.
- Tổng vẫn 4/6/8/10s → mỗi cú 2-4s: tự nhiên có nhịp cắt nhanh + cắt TRƯỚC khi model kịp morph.
- Giới hạn: cú 2-4s KHÔNG hợp cảnh ngấm cần cú dài liên tục — cảnh đó để 1 cú như cũ.
- **ĐÃ kiểm chứng nội bộ 1 mẫu (2026-07-12):** r2v 8s + 2 anchor, 3 cú cắt CỨNG đúng mốc ±0.2s,
  nhân vật/ánh sáng nhất quán xuyên cú. 1 mẫu ≠ khái quát → beat coverage đầu tiên của MỖI dự án
  vẫn phải nằm trong CLIP THỬ (GATE 2) trước khi tin cả batch (nguyên lý clip thử = cảnh rủi ro nhất).
- Khai báo qua `scenes[].shots[]`, compiler tự ghép (xem §7 + `project-schema.md`).

### 6b · Master frame → ingredient (opt-in, +1-2 gen mỗi beat) [nguồn Flow Help]

Flow cho **save frame từ clip đã gen** làm ảnh ingredient/khung đầu cho generation sau:
gen master wide → save frame khoảnh khắc đắt → frame làm neo KHÔNG GIAN + anchor nhân vật làm neo
DANH TÍNH → regen cú cận với prompt tả cỡ cảnh mới. Dùng khi timestamp không đạt (cần cú cận dài
hơn 4s, hoặc mốc thời gian không nghe lời). Rủi ro thật: mặt drift ở close-up, ánh sáng chỉ "gần
khớp" → cần keo hậu kỳ (grade + ambience liền, Stage 4) và chèn insert giữa 2 cú lệch (§2).
Đừng gen mặt ở góc cực đoan (bird's eye/worm's eye) — model khó giữ nét mặt.

### 6c · Punch-in crop tại bàn ráp (0 credit, kỹ thuật dựng cổ điển)

Crop 20-40% từ master làm "cú medium giả" — KHÔNG gen gì thêm. Cảnh giác độ phân giải: nguồn
1080p crop 30% rồi phóng lại là mềm hình; pipeline hiện scale 720→1080 thì càng thiếu pixel dư.
Chỉ dùng cho cú chèn NGẮN (1-2s) hoặc khi có nguồn 4K.

## 7 · Quy tắc kích hoạt — field continuity hết mồ côi

Bài học đo được: field CÓ trong schema mà 0/15 cảnh dùng = tri thức không thành hành vi. Từ nay
dựng storyboard (Bước 3) đi qua bảng này cho TỪNG cặp cảnh liền kề:

| Nếu... | Thì PHẢI cân nhắc | Ghi chú |
|---|---|---|
| Beat `role: hook/turn/payoff` hoặc có `dialogue[]` | `shots[]` 2-3 cú (coverage §6a) | Ít nhất 1 cú cận/insert/reaction trong đó |
| 2 cảnh liên tục thời gian + không gian (hành động chảy liền) | `link_prev: true` (frame-chain) | Đổi bối cảnh hoàn toàn thì ĐỪNG bật |
| 2 cảnh cùng sự kiện, đổi cỡ cảnh | `match_cut_with` + `subject_position` khớp | Cắt giữa động tác (match on action) |
| Cảnh ĐẦU TIÊN ở location mới | `shot_size: wide/establishing` (re-establish) | Trừ khi phá có chủ đích (§3, ghi lý do) |
| Hội thoại 2 nhân vật ≥2 lượt | Khai trục 180°: A `subject_position: right`, B `left`, giữ suốt cảnh | Kèm luật thoại-né-close-up (`vo-writing-craft §7`) |
| Chuỗi ≥3 cảnh cùng `camera_angle` | Đổi góc HOẶC ghi lý do trục điểm nhìn vào kichban.md | QC sẽ warn |
| Sự kiện nặng vừa xảy ra | Cảnh lặng 1 cú dài (KHÔNG coverage) | Khớp `vo-writing-craft §5` |

`flowgen qc-storyboard` đo các luật đo-được ở trên và WARN (không chặn — luật điện ảnh là mặc định
để phá có chủ đích; máy đo, người quyết ở GATE 1B).

## Map vào stage / QC

- **Stage 1 (vidgen-script) Bước 3** — đọc file này TRƯỚC khi điền field/`shots[]`; Bước 4 chạy
  `flowgen qc-storyboard` trước khi trình GATE 1B.
- **Stage 2 (vidgen-character)** — dự án có cảnh `shots[]` → clip thử NÊN là 1 cảnh coverage
  (đo độ nghe lời timestamp sớm).
- **Stage 4 (vidgen-assemble)** — keo dán hậu kỳ cho cú regen lệch nhẹ: ambience liền xuyên cắt +
  grade thống nhất (đợt sau).
- Checklist bổ sung GATE 1B: ☐ beat đắt có coverage (hoặc lý do không) ☐ duration biến thiên theo
  beat, không chuỗi ≥4 cảnh cùng độ dài vô cớ ☐ không chuỗi ≥3 cảnh trùng camera_angle vô cớ
  ☐ transition mặc định cut, fade/dissolve nêu được nghĩa ☐ đổi location có re-establish
  ☐ cặp cảnh liền kề đã đi qua bảng kích hoạt §7.

## Nguồn (vững vs mẹo)

**Quy ước dựng phim vững (kinh điển):**
- Steven D. Katz, *Film Directing: Shot by Shot* — coverage, staging, triangle principle.
- Walter Murch, *In the Blink of an Eye* — Rule of Six (thang ưu tiên do Murch đặt, không phải đo).
- Karel Reisz & Gavin Millar, *The Technique of Film Editing* — continuity editing gốc.
- Hollywood continuity system (180°/30°/eyeline/match-on-action) — chuẩn công nghiệp từ 1930s.
- StudioBinder (Rule of Six, eyeline match, cutaway) — đối chiếu thuật ngữ, KHÔNG lấy số marketing.

**Kỹ thuật Veo/Flow (nguồn chính thức):**
- Timestamp prompting nhiều cú/1 gen: cloud.google.com/blog/products/ai-machine-learning/ultimate-prompting-guide-for-veo-3-1
- Save frame làm ingredient/khung đầu: support.google.com/flow/answer/16935718
- Ingredients to Video (3 ảnh ref): support.google.com/flow/answer/16353334

**Mẹo cộng đồng (nhất quán nhiều nguồn nhưng chưa kiểm chứng độc lập — dùng thận trọng):**
- Clip AI đạt đỉnh 4-6s đầu, cuối generation hay rã → gen dài hơn nhu cầu rồi cắt.
- Giữ cố định ≥2 neo (background/motion/lens/expression) mỗi lần đổi cỡ cảnh kẻo mặt trôi.
- ĐÃ LOẠI: mọi số % retention trong bài SEO/Medium không nguồn; case study "Flow giảm 47→2 phút" (bịa).
