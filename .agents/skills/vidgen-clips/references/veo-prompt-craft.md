# Veo/Flow prompt craft — viết prompt điện ảnh cho AI video (Stage 3 · vidgen-clips)

Vùng bằng chứng MẠNH nhất của cả bộ (nguồn chính thức Google DeepMind + Google Cloud, verify 3-0).
Dùng khi viết `scenes[].prompt` (storyboard) và khi gen clip.

## 1 · Prompt = LẮP GHÉP từ khối thành phần, không phải 1 câu mơ hồ

Bằng chứng (confidence CAO, nguồn chính thức):
- **Veo 3 (DeepMind)** — 7 khối: **framing/chuyển động máy + style + ánh sáng + mô tả nhân vật +
  bối cảnh + hành động + lời thoại**.
- **Veo 3.1 (Google Cloud)** — công thức 5 phần, ghép đúng thứ tự:
  **`[Cinematography] + [Subject] + [Action] + [Context] + [Style & Ambiance]`**.

Càng chi tiết từng khối → càng kiểm soát output. Mẫu điền:
```
[Cinematography] Medium shot, slow push-in, eye-level, shallow depth of field.
[Subject] <mô tả nhân vật NHẮC LẠI nguyên văn từ characters[].desc>.
[Action] <1 hành động chính, rõ ràng>.
[Context] <bối cảnh/địa điểm/thời điểm>.
[Style & Ambiance] <style chung của dự án LẶP NGUYÊN VĂN> + <ánh sáng> + <mood>.
```
- **Lặp NGUYÊN VĂN** style chung (art style, palette, lighting) ở mọi cảnh → các cảnh đồng bộ.
- **KHÔNG yêu cầu chữ trong hình** (sub burn sau). `flowgen scene-images` tự nối "no text…" chống
  AI bịa chữ/thư pháp; tắt bằng `--allow-text`.
- **Continuity địa điểm:** cảnh liền kề cùng bối cảnh → lặp NGUYÊN VĂN cụm mô tả địa điểm.

## 1b · Coverage trong 1 generation — TIMESTAMP PROMPTING (Veo 3.1)

Bằng chứng (nguồn chính thức Google Cloud): Veo 3.1 nhận prompt đánh **mốc thời gian** để gen
NHIỀU cú cắt xen trong CÙNG 1 lần gen — cách rẻ nhất (0 credit thêm) để 1 khoảnh khắc có
wide + close + insert như phim, các cú tự nhất quán (chung generation):
```
[00:00-00:03] Wide shot, eye-level: the old woman presses a sweet potato into the girl's hands.
[00:03-00:06] Close-up: the girl's face, eyes widening, she looks up.
[00:06-00:08] Extreme close-up, insert: the potato in her small hands, steam rising.
```
- Khai báo qua `scenes[].shots[]` — `flowgen compile-prompts` tự ghép đúng định dạng (thiết lập
  chung subject+context trước, chuỗi mốc sau, style cuối). Mỗi cú 2-4s; tổng ≤ `duration`.
- **Độ nghe lời mốc CHƯA kiểm chứng độc lập** → cảnh coverage đầu tiên phải nằm trong CLIP THỬ
  (GATE 2). Không đạt → hạ về 1 cú, hoặc đường B: **save frame trong Flow** (chính thức, Flow Help)
  — trích frame master làm ingredient/khung đầu regen cú cận (+1-2 gen; mặt có thể drift ở close-up,
  ánh sáng chỉ gần khớp — chèn insert giữa 2 cú lệch để mắt "reset").
- Khi nào NÊN coverage, tiến trình cỡ cảnh, luật 30°/match-cut giữa các cú: thiết kế ở tầng
  storyboard — `vidgen-script/references/scene-grammar.md` (§2-§7).

## 2 · Vựng từ điện ảnh → đưa thẳng vào prompt (điền `shot_size`, `camera_move`)

**Cỡ cảnh (`shot_size`)** — đa dạng giữa các cảnh liền kề:
- `establishing` / "wide establishing shot" · `wide` · `medium` / "medium shot" · `close` /
  "close-up" · `extreme_close` / "extreme close-up, macro detail" · "over-the-shoulder" · "bird's eye / top-down".

**Chuyển động máy (`camera_move`)** — có chủ đích, mỗi cảnh 1 kiểu:
- Tuyến: "slow push-in" · "pull-out dolly" · "lateral tracking" · "crane up/down" · "tilt up/down".
- Quỹ đạo: "180-degree orbit" · "360-degree orbit" · "ascending/descending spiral".
- Đặc biệt: "whip pan" · "dolly zoom" · "crash zoom" · "follow-behind" · "first-person POV" ·
  "handheld" · "rack focus". Tĩnh: "static, locked-off".

**Ánh sáng / bố cục** (rải vào [Style & Ambiance]): "backlit with rim light" · "golden hour" ·
"soft ambient" · "atmospheric moody lighting" · "shallow depth of field at f/2.8" · "symmetrical
center frame" · "creamy bokeh" · "cinematic, photorealistic". Bố cục cổ điển: rule of thirds,
headroom hợp lý, leading lines (đưa vào mô tả cảnh khi cần).

## 2b · Tỉ lệ & tương quan vật thể (scale) — thuộc tính của THẾ GIỚI, không của định dạng

Bằng chứng (verify): Veo điều khiển scale bằng **prompt keyword** (shot_size + camera_angle + cụm
quan hệ tường minh) VÀ **neo theo ảnh anchor** — tỉ lệ đã có trong location/character anchor được Veo
bảo toàn qua các cảnh. Nguồn: veo3ai.io/blog/veo-3-image-reference-workflow-2026 (anchor neo scale),
medium.com/@yardenhazan (forced perspective = angle × shot_size).

**Nguyên tắc lõi:** scale KHÔNG bắt buộc chuẩn đời thực — nó do **style/thế giới** quyết. Chọn 1
archetype, dán keyword mồi vào `style` project-level → mọi cảnh thừa hưởng (sửa 1 chỗ, không chỉnh từng cảnh):

| Archetype | Loại video hay gặp | Quy ước scale | Keyword mồi (vào `style`/prompt) |
|---|---|---|---|
| **true_to_life** | vlog, tài liệu, tin tức, hướng dẫn | Đúng đời thực (cây 3–15× người tùy loài, nhà đúng tỉ lệ) | `accurate real-world scale, natural proportions, believable size relationships` |
| **heroic** | kể chuyện, quảng cáo thương hiệu | Hơi phóng đại tạo uy nghi, KHÔNG phá vật lý — nhấn bằng low-angle | `slightly heroic scale, low-angle grandeur, imposing presence` |
| **monumental** | sử thi, thần thoại, trailer epic | Contrast kịch tính: thiên nhiên/kiến trúc khổng lồ nuốt chửng người tạo awe | `colossal scale, monumental nature dwarfing tiny humans, awe-inspiring vastness` |
| **storybook** | cổ tích, thiếu nhi, hoạt hình | Cách điệu dễ thương, vật thân thiện phóng đại nhẹ, không đáng sợ | `stylized storybook proportions, friendly rounded scale, cozy` |
| **hero_product** | quảng cáo sản phẩm | Sản phẩm phóng to làm tâm điểm, môi trường thu nhỏ/tối giản | `hero product scale, product enlarged as focal centerpiece` |

**Đòn bẩy cơ học (dùng field SẴN CÓ, không thêm field):**
- `shot_size`: "extreme long shot" → chủ thể tí xíu giữa khung (nhấn sự nhỏ bé); "close/macro" → vật choán khung.
- `camera_angle`: "worm's eye / low angle" → vật vươn cao áp đảo; "high angle / bird's eye" → chủ thể nhỏ bé, dễ tổn thương.
- **Cụm quan hệ tường minh** trong prompt: `towering over`, `dwarfing`, `miniature beside`, `only/exactly <số>` (Veo tuân số lượng tốt tới ~15 vật cùng loại, quá thì gộp/mờ).

**Bake vào anchor cho scale phi-thực NHẤT QUÁN:** muốn tỉ lệ lệch-thực giữ y hệt qua mọi cảnh (vd cây
khổng lồ cạnh người) → dựng sẵn tỉ lệ đó trong **location anchor** (Grid Method, xem vidgen-character
Bước 2b); Veo neo giữ. Chỉ dùng prompt keyword thì scale có thể trôi giữa các cảnh.

## 2c · Style reference phải CỤ THỂ — neo ở `style` project-level, KHÔNG rải per-scene

Bằng chứng (verify): từ mô tả style **mơ hồ** ("cinematic", "high quality", "professional", "4k",
"masterpiece") model **không đổi output** — chúng là nhiễu. Model chỉ phản hồi **neo cụ thể**:
- **Camera body / ống kính:** `"shot on Arri Alexa"`, `"shot on iPhone 15 Pro"`, `"35mm film grain"`,
  `"anamorphic lens flare"`.
- **Director / DoP style:** `"Wes Anderson style"`, `"David Fincher style"`, `"Roger Deakins cinematography"`.
- **Color grade tường minh:** `"teal and orange grade"`, `"golden hour grade"`, `"desaturated cold grade"`,
  `"high-contrast noir"`.

**Ranh giới — neo Ở ĐÂU (quan trọng nhất):** style-reference đặt look TOÀN video → phải nằm ở field
**`style` project-level**, để `compile-prompts` **lặp NGUYÊN VĂN vào mọi cảnh** (xem §1). Rải camera
body / director / grade **lẻ theo từng cảnh** = mỗi cảnh một look → **phá nhất quán** (lỗi kinh điển
video AI ghép cảnh, §6). Cảnh phá lệ có chủ đích → dùng `prompt_override`, KHÔNG sửa lẻ `style`.

**Luật vague-term:** từ mơ hồ ("cinematic", "photorealistic"…) chỉ dùng khi **KÈM ≥1 neo cụ thể**
(camera body / grade / director). Đứng một mình thì **bỏ** — nó chiếm chỗ prompt mà không điều khiển gì.
→ Sửa lại các mô tả kiểu "cinematic, photorealistic" ở §2: giữ nếu đã có neo cụ thể đi kèm trong `style`,
bỏ nếu đứng trơn.

## 3 · Âm thanh sinh cùng video (Veo 3)

Bằng chứng (confidence cao, nguồn chính thức): Veo 3 **sinh audio đồng bộ ngay từ text prompt** —
nêu (đặt tên) âm thanh muốn nghe để khớp hình:
- SFX: `"crunchy typing sounds"`, `"thunder cracks in the distance"`.
- Ambience: `"the quiet hum of a starship bridge"`, `"gentle rain ambience"`.
- Thoại: đặt trong dấu ngoặt kép trong khối lời thoại.
→ Giảm phụ thuộc SFX rời ở hậu kỳ. LƯU Ý pipeline: Veo gắn audio vào clip; assemble mặc định `-an`
(bỏ audio gốc) để nhường giọng đọc ElevenLabs. Nếu MUỐN giữ audio Veo (cảnh không lời đọc), cân
nhắc giữ — nhưng mặc định story/reel có VO thì bỏ.

## 4 · Negative prompt — cụ thể, không chung chung (tránh AI-tell)

Bằng chứng (verify): negative CHUNG CHUNG ("bad quality", "ugly", "low resolution") **không ăn**;
model phản hồi với negative CỤ THỂ:
- "steady camera movement" · "controlled motion" · "stable facial features" · "consistent proportions".
- Chống AI-tell (thừa ngón, méo mặt, morphing): mô tả DƯƠNG bản rõ ("five fingers, natural hands",
  "consistent face") thay vì chỉ cấm; giảm hành động tay phức tạp/nhanh trong 1 cảnh.

## 5 · Khi Flow/Veo từ chối hoặc chặn ngầm

- `No media in response` = prompt bị chặn → viết lại trung tính hơn, bỏ từ nhạy cảm.
- `500 Failed to download` lặp ≥2 lần cùng 1 cảnh = **Veo chặn NGẦM nội dung ảnh** (người trong
  suốt/ma/phát sáng xuyên thấu…). KHÔNG retry quá 2-3 lần → đổi concept ảnh cảnh đó, hoặc để
  `failed` (assemble tự fallback Ken Burns từ ảnh tĩnh). Xem thêm bảng sự cố trong SKILL.md.

## 6 · Continuity giữa cảnh — chống 2 lỗi kinh điển của video AI ghép cảnh

Nguồn: CinematicHubClone (ScriptShot/ScriptScene/EditingTransitions) — quy ước điện ảnh, không số liệu.
AI video mỗi cảnh gen độc lập → hay tự đảo hướng/nhảy setting. Ràng buộc bằng field + prompt:

- **Luật 180° / screen direction (`screen_direction`):** giữ hướng chuyển động nhất quán qua các cảnh
  (nhân vật đi trái→phải thì cảnh sau vẫn trái→phải, trừ khi có cú chuyển có chủ đích). Ghi RÕ hướng
  vật lý trong prompt ("moving left to right") — AI hay tự lật. Compiler đưa `screen_direction` vào [Cinematography].
- **Match cut (`match_cut_with`, `subject_position`):** nối 2 cảnh qua trùng hình-thái/chuyển động
  (xương xoay → trạm vũ trụ; vòng tròn → mặt trời). Đặt chủ thể cùng vị trí khung 2 cảnh để mắt trôi mượt.
- **Beat-breakdown cho hành động:** ĐỪNG gen 1 combat/hành động phức tạp 10s trong 1 cảnh (Veo morph
  giữa frame). Chia 3-4 cảnh nhỏ (tụ lực → vung → va chạm → bật lùi), mỗi cảnh 1 `action` rõ.
- **Giới hạn góc máy:** không quay 360° quanh nhân vật trang phục phức tạp trong 1 cảnh (dễ méo/morph) —
  chia nhỏ shot. Cảnh close-up mặt → nhấn "consistent face matching reference".
- **Scene-as-asset:** gom hành động vào CÙNG location (khoá bối cảnh, xem vidgen-character Bước 2b);
  đổi location thì bắc cầu qua yếu tố môi trường, đừng nhảy đột ngột.

Ranh giới rõ: `screen_direction`/`match_cut_with` là **continuity NỘI DUNG** (đưa vào prompt/lên kế
hoạch cảnh); còn `transition.type` (xfade/dissolve) là **hiệu ứng BIÊN TẬP** ở Stage 4 — hai thứ khác nhau.

## X · Ranh giới ảnh→video: nội dung engine chặn ở tầng VIDEO (không lộ ở tầng ảnh)

**Nguyên lý:** tầng ảnh (T2I, rẻ) và tầng video (I2V/T2V, đắt) có **safety filter KHÁC nhau**. Ảnh gen
được KHÔNG bảo đảm video gen được — đây là ranh giới có giả định ngầm hay gây vỡ batch. Triệu chứng khi
bị chặn: `MEDIA_GENERATION_STATUS_FAILED` (khác lỗi `400 invalid argument` = tạm thời, gen lại là qua).

**Vùng nội dung Veo hay chặn ở tầng video** (quan sát thực chiến, không phải danh sách chính thức):
- **Trẻ em + đau khổ/suy kiệt thân thể** (đói, gầy trơ, bệnh, thương tích) — ca đã gặp và giải được.
- Bạo lực rõ, máu me, vũ khí chĩa vào người, nội dung y tế cận cảnh, hành hạ.

**Cách viết vượt (giữ được ý đồ, không né chủ đề):** diễn cái khổ qua **HOÀN CẢNH**, đừng tả **THÂN THỂ**.

| Từ trigger (tránh trong prompt VIDEO) | Viết thay bằng |
|---|---|
| `gaunt`, `frail`, `emaciated`, `skeletal`, `starving` | quần áo vá rách, bối cảnh tiêu điều, biểu cảm buồn, bát ăn vơi |
| `dying`, `suffering`, `agony`, `corpse` | ngồi lặng, ánh mắt xa xăm, khói hương, không gian trống |
| động tác đau đớn cực đoan | cử chỉ dịu (ôm, chia sẻ, cúi đầu), thêm tông ấm/hiền |

- Ảnh khung đầu (I2V input) cũng bị soi — nếu ảnh quá cực đoan, làm dịu ảnh trước, đừng chỉ sửa prompt.
- **Fallback khi vẫn chặn:** ảnh gen được → dùng ảnh tĩnh + Ken Burns (assemble tự làm cho cảnh `failed`),
  đừng để 1 cảnh chặn cả video. Xem `vidgen-assemble/SKILL.md` (fallback zoompan).
- **Đặt bẫy này ở clip thử:** chọn cảnh rủi ro nhất làm clip thử (xem `vidgen-character` Bước 3) để lộ giới hạn SỚM.

## Map vào stage

- **Storyboard (Stage 1):** điền field craft → `flowgen compile-prompts` ghép ra `scenes[].prompt`
  (5 khối trên, hoặc chuỗi timestamp nếu cảnh có `shots[]` — mục 1b) tự động; viết tay thì bật
  `prompt_override`. `shot_size`/`camera_angle`/`camera_move`/`lighting`/`atmosphere`/`sfx`/
  `screen_direction` là nguyên liệu compiler. Chi tiết compiler:
  `vidgen-script/references/project-schema.md` (mục "Field craft chi tiết + PROMPT COMPILER").
  Trước GATE 1B chạy `flowgen qc-storyboard` (đo nhịp/góc/transition/continuity, warn-only).
- **Gen clip (Stage 3):** flowgen dùng character + location anchor làm ref (≤3), đọc `prompt` đã compile.
- Checklist gate: prompt có đủ 5 khối? style lặp nguyên văn? đặc điểm nhân vật nhắc lại? có
  shot_size/camera_move rõ? screen_direction nhất quán mạch? không yêu cầu chữ trong hình?
  tỉ lệ vật-với-vật khớp style archetype (mục 2b)?

## Nguồn (verify 3-0, nguồn chính thức)

- deepmind.google/models/veo/prompt-guide (Veo 3: 7 khối, audio đồng bộ)
- cloud.google.com/blog/products/ai-machine-learning/ultimate-prompting-guide-for-veo-3-1 (5 phần)
- james-palm.medium.com/veo3-camera-movements-shot-types-prompts (vựng camera/shot)
- artlist.io/blog/negative-prompts-ai-video (negative cụ thể)
- veo3ai.io/blog/veo-3-image-reference-workflow-2026 + medium.com/@yardenhazan (scale: anchor neo + forced perspective)
