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

## Map vào stage

- **Storyboard-prompt (Stage 1 điền `prompt`)** + **gen clip (Stage 3)**. `shot_size`/`camera_move`
  trong manifest → nhắc người/skill đưa vựng từ trên vào prompt.
- Checklist gate: prompt có đủ 5 khối? style lặp nguyên văn? đặc điểm nhân vật nhắc lại? có
  shot_size/camera_move rõ? không yêu cầu chữ trong hình?

## Nguồn (verify 3-0, nguồn chính thức)

- deepmind.google/models/veo/prompt-guide (Veo 3: 7 khối, audio đồng bộ)
- cloud.google.com/blog/products/ai-machine-learning/ultimate-prompting-guide-for-veo-3-1 (5 phần)
- james-palm.medium.com/veo3-camera-movements-shot-types-prompts (vựng camera/shot)
- artlist.io/blog/negative-prompts-ai-video (negative cụ thể)
