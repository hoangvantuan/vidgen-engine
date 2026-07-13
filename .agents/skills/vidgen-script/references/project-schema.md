# Schema `project.json` — manifest dự án vidgen

Manifest là NGUỒN SỰ THẬT duy nhất về trạng thái dự án. Script chỉ ghi các field nó sở hữu
(`media_id`, `status`); Claude sửa phần còn lại bằng Edit. Ghi atomic — an toàn khi hỏng giữa chừng.

```json
{
  "name": "con-cao-va-chum-nho",
  "preset": "story",                    // "story" (kể chuyện dài) | "reel" (ngắn 20-60s)
  "aspect": "portrait",                 // "portrait" 9:16 | "landscape" 16:9
  "language": "vi",
  "voice_id": "",                       // ElevenLabs voice id của NARRATOR (giọng kể). Rỗng = video không lời đọc.
                                        // Thoại nhân vật dùng characters[].voice_id riêng (xem dưới).
  "flow_project_id": "",                // rỗng = dùng DEFAULT_PROJECT của omniflash

  "hook": {                             // MỞ ĐẦU — nơi tụt người xem mạnh nhất (short-form ~3s, long-form ~30s)
    "promise": "",                      // lời hứa/tò mò khán giả nhận NGAY giây đầu (open loop)
    "first_frame": "",                  // mô tả frame hình đầu tiên gây tò mò → đưa vào prompt cảnh mở
    "spoken": ""                        // câu VO đầu tiên, mạnh nhất — đặt lên đầu
  },
  "music": {                            // nhạc nền — auto-pick theo mood hoặc chỉ định file
    "mood": "",                         // calm|tense|uplifting|sad|epic|playful|neutral (rỗng = không nhạc)
    "file": "",                         // nhạc cụ thể (ưu tiên hơn mood; CLI --bgm override cả hai)
    "ambience": ""                      // (tùy chọn) ROOM TONE liền mạch — mô tả EN lớp nền không gian
                                        //   ("quiet village night, soft wind, distant crickets, continuous
                                        //   ambient bed, no melody, seamless loop"). CÓ CONSUMER:
                                        //   gen_sfx.py --ambience gen 1 file 22s → assemble loop-crossfade
                                        //   phủ TRỌN video, volume thấp KHÔNG ducking — keo dán số 1 của
                                        //   ngành dựng: lớp âm LIỀN xuyên mọi cắt "dán" clip gen rời thành
                                        //   một không gian. KHÁC sfx[] (sự kiện, đặt theo cảnh) và mood (nhạc).
  },

  "endcard_tagline": "",                // (tùy chọn) Ô BIẾN THIÊN 1 DÒNG của end-card brand — CONSUMER:
                                        // make_props.py (Remotion overlay). Đổi theo phẩm chất video.
                                        // Rỗng → fallback lấy defaultTagline của brand preset. Khung
                                        // intro/end-card còn lại (logo bloom→watermark, hero nở, wordmark
                                        // + url, nốt chuông, lời CTA) là CỐ ĐỊNH theo preset neo nhận diện
                                        // — không tham số hoá. Brand nạp qua apply_brand.py --brand <tên>.

  "style": "",                          // (tùy chọn) STYLE CHUNG toàn dự án — art style + palette + medium/lens
                                        // vd "3d donghua style, warm cinematic grading, shot on 35mm, 8k".
                                        // DÙNG NEO CỤ THỂ (camera body/director/color grade), tránh vague
                                        // "cinematic/high quality/professional" đứng trơn — xem veo-prompt-craft §2c.
                                        // Kèm QUY ƯỚC SCALE ở đây (tỉ lệ vật-với-vật do THẾ GIỚI quyết, không bắt
                                        // buộc chuẩn đời thực): chọn 1 archetype (true_to_life/heroic/monumental/
                                        // storybook/hero_product) → dán keyword mồi. Bảng: vidgen-clips/references/
                                        // veo-prompt-craft.md mục 2b. Scale lệch-thực nhất quán → bake vào location anchor.
                                        // compiler nhét NGUYÊN VĂN vào [Style & Ambiance] mọi cảnh → đồng bộ.

  "gates": {                            // 5 cổng human — orchestrator kiểm trước khi đi tiếp
    "story_lock": false,                // GATE 1A: KỊCH BẢN (through-line/mạch/hook/lời VO) đã duyệt — CHẶN element pass
    "element_lock": false,              // GATE 1A2: BẢNG ELEMENT (mọi nhân vật/prop/location/ambience tách từ
                                        //   kịch bản → characters[]/props[]/locations[] + 01_script/elements.md,
                                        //   kèm cách khoá + tần suất) đã duyệt — CHẶN dựng storyboard. Storyboard
                                        //   chỉ được TRỎ id từ bảng element; id lạ = lỗi cứng (QC nhóm THỰC THỂ).
                                        //   Lý do gate riêng: danh sách element phải được nhìn TOÀN BỘ một lượt
                                        //   TRƯỚC khi rải vào N cảnh (bệnh nhân-vật-mồ-côi sinh từ thiếu bảng kiểm này).
    "script_lock": false,               // GATE 1B: storyboard/prompt (field/cỡ cảnh/continuity) đã duyệt
    "character_lock": false,            // GATE 2: anchor + clip thử đã duyệt
    "final_approved": false             // GATE 3: bản ráp cuối đã duyệt
  },
  // Backward-compat: dự án cũ THIẾU story_lock/element_lock → orchestrator coi như đã mở (không chặn luồng cũ).
  // Luật gen: story_lock=false → CẤM element pass. element_lock=false → CẤM dựng storyboard/compile.
  // script_lock=false → CẤM gen.

  "characters": [
    // LUẬT ĐỒNG BỘ (không phân biệt chính/phụ): MỌI nhân vật xuất hiện MẶT-RÕ (medium trở gần)
    // hoặc lặp ≥2 cảnh PHẢI có entry + anchor riêng (1 người/ảnh — sheet chung nạp vào Flow là
    // Veo TRỘN MẶT, xem consistency-and-ai-tells.md §1). Đám đông/người nền → KHÔNG entry,
    // viết action né mặt: "turned away", "silhouette", "out of focus". QC bắt nhân vật mồ côi
    // (danh từ người trong action mà không khai characters) — flowgen qc-storyboard nhóm F.
    {
      "id": "be_na",
      "desc": "bé gái 5 tuổi, tóc hai bím, váy vàng, mắt to",   // NHẮC LẠI trong prompt mỗi cảnh
      "voice_id": "",                                          // (tùy chọn) ElevenLabs voice id RIÊNG cho thoại
                                                               //   nhân vật này (scenes[].dialogue[]). Rỗng → dùng
                                                               //   giọng narrator. Xem "Đa giọng" cuối file.
      "voice_pitch": 0,                                        // (tùy chọn) dịch cao độ giọng nhân vật này (nửa cung).
                                                               //   tts_to_ass.py ĐỌC & áp TỰ ĐỘNG (đường đa giọng),
                                                               //   giữ nguyên độ dài → timestamp không xô. Narrator
                                                               //   KHÔNG bị đụng. VD giọng bé: +2 (giọng kể ≠ giọng bé).
      "sheet": "02_characters/be_na_sheet.png",                 // MASTER DESIGN SHEET (turnaround + expressions +
                                                                //   poses + accessories + palette + companion) —
                                                                //   cho NGƯỜI duyệt + nguồn derive anchor,
                                                                //   TUYỆT ĐỐI không nạp vào Flow (Veo trộn mặt)
      "anchors": [                                              // anchor — cho MÁY: 1 người/ảnh, 1 góc, nền trơn.
                                                                // Nhân vật CHÍNH: ĐỦ GÓC theo turnaround
                                                                // (front/3q_front_left/3q_front_right/left/right/back);
                                                                // vai phụ ít cảnh: tối thiểu front + side.
        { "angle": "front", "file": "02_characters/be_na_front.png", "media_id": "" },
        { "angle": "side",  "file": "02_characters/be_na_side.png",  "media_id": "" }
      ]
    }
  ],

  "locations": [                        // (tùy chọn) KHOÁ BỐI CẢNH — anchor môi trường, giữ setting đồng nhất
    {                                   //            xuyên các cảnh cùng địa điểm (như anchor giữ nhân vật)
      "id": "cafe",
      "desc": "quán cà phê gỗ ấm, cửa sổ lớn phía đông, ánh nắng sớm, cây xanh",  // NHẮC LẠI trong prompt
      "sheet": "02_locations/cafe_grid.png",   // Grid 3×3 nhiều góc trong 1 render — cho NGƯỜI duyệt (xem mục dưới)
      "anchors": [                             // anchor bối cảnh — cho MÁY: nền địa điểm, KHÔNG người, style chung.
                                               // QUY ƯỚC ĐỦ 9 GÓC từ Grid 3×3 ngay khi khoá bối cảnh (wide/corner/
                                               // reverse/left/right/high/low/detail/entrance — đặt angle theo grid);
                                               // cảnh dùng góc thiếu anchor = Veo tự bịa layout → lệch nhà cửa/cây.
                                               // Prop GẮN BỐI CẢNH (nồi, chum, bàn thờ…) BAKE THẲNG vào ảnh anchor
                                               // này (Veo neo theo, không tốn slot ref riêng) + khai props[] để có desc.
        { "angle": "wide",  "file": "02_locations/cafe_wide.png",  "media_id": "" },
        { "angle": "corner", "file": "02_locations/cafe_corner.png", "media_id": "" }
      ]
    }
  ],

  "props": [                            // (tùy chọn) REGISTRY ĐẠO CỤ — nguồn sự thật duy nhất cho mọi prop
    {                                   //   lặp ≥2 cảnh (hết cảnh này tả "bát cháo" một kiểu, cảnh kia kiểu khác)
      "id": "cu_khoai",
      "desc": "a small roasted sweet potato, golden-brown mottled skin, wisps of steam",
                                        // compiler chèn NGUYÊN VĂN vào [Subject] mọi cảnh có prop này
      "hero": true,                     // hero-prop = gần camera / mang nghĩa truyện → PHẢI có anchor ảnh
      "anchor": { "file": "02_props/cu_khoai.png", "media_id": "" }
                                        // ảnh anchor prop (T2I miễn phí, nền trơn, style đồng bộ mọi anchor).
                                        // flowgen đưa vào slot ref khi còn chỗ + compose-frame dùng khi composite.
                                        // Prop KHÔNG hero: bỏ anchor, chỉ desc (đủ cho prop nền thoáng qua).
    }
  ],

  "scenes": [
    {
      "id": 1,
      "vo": "Lời đọc tiếng Việt của cảnh này.",   // rỗng nếu video không lời
      "prompt": "",                     // prompt hình tiếng Anh. ĐỂ RỖNG → compiler tự ghép từ field craft
                                        // bên dưới. Ghi tay = override luôn (compiler bỏ qua cảnh này).
      "mode": "i2v",                    // "i2v" (mặc định) | "t2v" | "r2v" | "fl"
      "duration": 8,                    // 4|6|8|10 — thời lượng gen; khi ráp sẽ setpts khớp lời đọc.
                                        //   BIẾN THIÊN theo beat, đừng để cả phim 1 độ dài (bài học 15/15
                                        //   cảnh 8.0s = slideshow): căng/hành động 4-6s, ngấm cảm xúc/lặng
                                        //   8-10s, leo thang cao trào thì NGẮN DẦN. Xem scene-grammar.md §5.
      "characters": ["be_na"],          // id nhân vật xuất hiện → flowgen tự chọn anchor làm ref.
                                        //   THỨ TỰ = ưu tiên slot ref (3 vé): xếp nhân vật mặt-rõ-gần-camera TRƯỚC.
      "angle": "front",                 // góc nhân vật trong cảnh → chọn anchor đúng góc
      "location": "cafe",               // (tùy chọn) id trỏ locations[] → chọn location anchor + lặp desc bối cảnh
      "props": ["cu_khoai"],            // (tùy chọn) id trỏ props[] registry → compiler chèn desc NGUYÊN VĂN,
                                        //   flowgen thêm anchor hero-prop vào slot ref nếu còn chỗ
      "role": "hook",                   // (tùy chọn) vai trò mạch kể: hook|setup|development|turn|payoff|cta

      // ── State-tracking (tùy chọn) — SỔ LIÊN TỤC per cảnh, chống lệch logic xuyên cảnh ──
      "state": {                        // Claude điền ở stage script, người duyệt ở GATE 1B. QC đo phần đo được
                                        // (qc-storyboard nhóm G); phần ngữ nghĩa Claude soi checklist gate.
        "time_of_day": "dusk",          // dawn|morning|noon|afternoon|dusk|night — TRỐNG = KẾ THỪA cảnh trước.
                                        //   QC WARN khi chạy lùi (qua ngày mới → ghi chú kichban.md) hoặc
                                        //   mâu thuẫn lighting (night + golden_hour). Compiler đưa vào prompt.
        "weather": "overcast",          // trống = kế thừa. Compiler đưa vào [Style & Ambiance].
        "wardrobe":  { "be_na": "same worn brown clothes, hem now dusty" },
                                        //   per nhân vật — compiler NỐI vào desc trong [Subject] (chỉ phần
                                        //   THỊ GIÁC vào prompt; đừng nhồi tiểu sử — prompt có ngân sách chú ý)
        "condition": { "be_na": "weak from hunger, dirt smudged on cheeks" },   // thể trạng NHÌN THẤY được
        "held_props": { "be_na": ["cu_khoai"] },   // prop trên tay ai — compiler chèn "holding <desc>"
        "position": "at the village gate, facing home"
                                        //   vị trí trong không gian — METADATA-ONLY cho QC/ledger + người soi
                                        //   teleport giữa cảnh; KHÔNG vào prompt (đã có action/context tả)
      },

      // ── Đồng bộ bằng ảnh cảnh trước (tùy chọn) ──
      "ref_prev": false,                // true (chỉ mode r2v): frame cuối NÉT clip cảnh trước làm 1 REF —
                                        //   giữ ánh sáng/layout khi CẮT ĐỔI GÓC cùng không gian (khác link_prev:
                                        //   không ép liền mạch chuyển động). LUẬT: ref_prev THAY location anchor
                                        //   (frame thật mạnh hơn anchor tĩnh), danh tính vẫn từ anchor GỐC
                                        //   (chống trôi photocopy); chỉ chain từ clip đã qua qc-clips.
      "composite": false,               // true: cảnh ĐÔNG thực thể (>3 ứng viên neo) → đường COMPOSITE
                                        //   FIRST-FRAME: flowgen compose-frame ghép dần từng thực thể vào
                                        //   1 khung hình đầu bằng edit ảnh (miễn phí), duyệt, rồi I2V.
                                        //   Né hẳn giới hạn 3 ref — mọi thứ khoá trong pixel. QC gợi ý cờ này.

      // ── Field craft chi tiết (tùy chọn) — compiler ghép thành prompt Veo tự nhiên ──
      "action": "a little girl reaches up and picks a ripe grape, smiling",  // HÀNH ĐỘNG chính (tiếng Anh, ngắn)
                                        //   → khối [Action]. Đây là NỘI DUNG cảnh compiler KHÔNG tự bịa được.
                                        //   Trống + prompt trống → compiler cảnh báo (không đủ liệu để ghép).
      "emotion": "wonder",              // (tùy chọn) cảm xúc chủ đạo: fear|tension|power|joy|sadness|romance|
                                        //   loneliness|chaos|calm|wonder — lighting/camera_angle/atmosphere bỏ
                                        //   trống thì compiler AUTO-FILL theo bảng emotion-recipe.md.
      "shot_size": "medium",            // (tùy chọn) cỡ cảnh: wide|medium|close|extreme_close|establishing — ĐA DẠNG giữa các cảnh
      "camera_angle": "eye_level",      // (tùy chọn) góc máy ĐIỆN ẢNH: eye_level|low|high|dutch|overhead|over_shoulder
                                        //   (KHÁC `angle` ở trên — `angle` là góc NHÂN VẬT để chọn anchor)
      "camera_move": "push_in",         // (tùy chọn) chuyển máy: static|push_in|pull_out|pan|tilt|orbit|handheld|crane
      "lighting": "golden_hour",        // (tùy chọn) preset ánh sáng: high_key|low_key|rembrandt|silhouette|rim|
                                        //   golden_hour|blue_hour|chiaroscuro|soft|hard (trống → auto theo emotion)
      "atmosphere": "",                 // (tùy chọn) khí quyển: rain|fog|smoke|god_rays|dust|snow|haze (trống → auto)
      "lens": "",                       // (tùy chọn) ống kính: wide_24|35mm|50mm|85mm|macro
      "sfx": ["gentle cafe ambience", "coffee cup clink"],   // (tùy chọn) hiệu ứng âm thanh — Veo 3 sinh audio đồng bộ
      "dialogue": [                     // (tùy chọn) thoại NHÂN VẬT — KHÁC `vo` (narration). CÓ CONSUMER (xem "Đa giọng").
        { "char": "be_na", "line": "Con tìm thấy rồi!" }   // char trỏ characters[].id → dùng voice_id của nhân vật đó
      ],                                //   MÔ HÌNH P1: cảnh có dialogue[] thì KHÔNG dùng `vo` — mỗi cảnh 1 kiểu tiếng.

      // ── SHOT — đơn vị sản xuất (workflow v2 shot-first). Scene = container ngữ nghĩa ──
      // Cảnh KHÔNG có shots[] → 1 cú như cũ (backward-compat tuyệt đối, image/clip cấp scene).
      // Có shots[] thì phân biệt 2 STYLE theo field (KHÔNG trộn 2 style trong 1 cảnh — QC bắt):
      //
      // STYLE 1 · SEPARATE (shot-first, MẶC ĐỊNH cho dự án mới): mỗi shot có `duration` riêng →
      //   MỖI SHOT 1 GENERATION RIÊNG (ảnh khung đầu riêng, clip riêng, duyệt/regen độc lập).
      //   Shot ĐẦU của cảnh ≥2 shot = MASTER (wide/establishing, thiết lập không gian + vị trí
      //   mọi người) — gen & duyệt TRƯỚC; shot con derive: ref = frame master + anchor gốc
      //   (danh tính LUÔN từ anchor — luật chống photocopy). Gen đủ shot → flowgen stitch-shots
      //   tự ghép (trim theo duration, cắt cứng) ra 04_clips/sceneNN.mp4 ĐÚNG hợp đồng cũ —
      //   assemble không đổi. Cảnh ngấm = 1 shot long-take duy nhất (đừng băm).
      "shots": [
        { "id": 1, "duration": 4, "shot_size": "wide", "camera_angle": "eye_level",
          "action": "an old woman presses a sweet potato into the girl's hands",
          "prompt": "",                 // DẪN XUẤT — compiler ghép per shot (cine của shot +
                                        //   subject/context/style/state của SCENE); prompt_override như scene
          "image": { "file": "03_images/scene05_s1.png", "media_id": "", "approved": false },
          "clip":  { "file": "04_clips/scene05_s1.mp4", "media_id": "", "status": "pending" } },
        { "id": 2, "duration": 3, "shot_size": "close",
          "action": "the girl's face, eyes widening, she looks up" },
        { "id": 3, "duration": 2, "shot_size": "extreme_close",
          "action": "insert: the sweet potato in her small hands, steam rising" }
      ],                                //   Tổng duration các shot ≈ duration cảnh (khớp VO — QC đo).
                                        //   duration gen Veo là 4/6/8/10 → shot ngắn hơn sẽ TRIM lấy đoạn ĐẦU
                                        //   khi stitch (đỉnh chất lượng 4-6s đầu — mẹo cộng đồng nhất quán).
      //
      // STYLE 2 · TIMESTAMP (biến thể micro-cut TRONG 1 generation — 0 credit thêm, đã kiểm
      //   chứng nội bộ 1 mẫu): mỗi cú có `from`/`to` (không duration/image riêng):
      //   { "from": 0, "to": 3, "shot_size": "wide", "action": "..." } — compiler ghép chuỗi
      //   "[00:00-00:03] ...". Tổng `to` ≤ duration cảnh, mỗi cú 2-4s. Dùng khi muốn nhiều cú
      //   mà chấp nhận không regen lẻ từng cú; Veo không nghe lời mốc thì chuyển separate.
      //   Khi có shots[] (style nào cũng vậy): shot_size/camera_angle/action TOP-LEVEL của scene
      //   bị bỏ qua (mỗi cú tự khai); emotion/lighting/style/subject/context/sfx/state vẫn áp CHUNG.

      // ── Continuity giữa cảnh (tùy chọn) — nối liền mạch, chống nhảy setting/đảo hướng ──
      "screen_direction": "L2R",        // hướng chuyển động trên khung: L2R|R2L|toward|away|static (giữ nhất quán mạch)
      "subject_position": "center",     // vị trí chủ thể: left|center|right — dùng cho match cut & nối vị trí
      "match_cut_with": null,           // id cảnh khác cần nối hình-thái/chuyển động giống (match cut)
      "link_prev": false,               // true → FRAME-CHAIN: lấy khung cuối NÉT của cảnh trước làm khung đầu
                                        //   cảnh này (nối liền mạch). scene-clips gen TUẦN TỰ; cần clip cảnh
                                        //   trước có sẵn. Bỏ ràng buộc "ảnh riêng đã duyệt" cho cảnh này.
      "prompt_override": false,         // true → prompt viết tay, compiler KHÔNG đụng cảnh này

      "image": { "file": "03_images/scene01.png", "media_id": "", "approved": false },
      "end_image": { "media_id": "" },  // mode "fl", hoặc frame-chain đợt 2 (khung cuối cảnh này)
      "clip": { "file": "04_clips/scene01.mp4", "media_id": "", "status": "pending" },
      // clip.status: "pending" | "done" | "failed"
      "transition": { "type": "cut" }
      // chuyển cảnh SAU cảnh này (sang cảnh kế). MẶC ĐỊNH là "cut" (hoặc bỏ field) — phim mặc
      // định CẮT; transition mềm là DẤU CÂU MANG NGHĨA, mỗi lần dùng phải trả lời "nghĩa gì ở đây?":
      // "dissolve" vào mơ/hồi tưởng · "fadewhite" tỉnh giấc/nhảy thời gian · "fade" đoạn dịu/thời
      // gian trôi. dur giữ 0.4-0.6s. Bài học đo được: 67% fade đồng loạt = keo an toàn vô nghĩa,
      // chính nó tạo cảm giác trôi đều slideshow. Xem scene-grammar.md §5.
    }
  ],

  "final": "06_final/final.mp4"
}
```

## Cấu trúc thư mục chuẩn (script tự tạo khi cần)

```
projects/<tên>/
├── project.json        # manifest này
├── 01_script/          # brief.md + kichban.md (bản cho người đọc/duyệt)
├── 02_characters/      # char sheet + anchors nhân vật
├── 02_locations/       # grid bối cảnh + anchors location (khoá setting)
├── 02_props/           # anchors hero-prop (khoá đạo cụ)
├── 03_images/          # ảnh khung đầu từng cảnh (T2I — miễn phí, gen tới khi ưng)
│                       #   sceneNN_comp_K.png = các lượt composite · sceneNN_chain.png = khung chain
├── 04_clips/           # clip từng cảnh (I2V — tốn credit, chỉ gen sau khi duyệt ảnh)
├── 05_audio/           # narration.mp3 + subs.ass + timings.json
├── 06_final/           # final.mp4
└── qc_clips/           # frame trích từ clip thật + ledger.md (flowgen qc-clips — soi lệch trước ráp)
```

## Quy tắc điền storyboard (chống lỗi hay gặp)

- `prompt` viết **tiếng Anh**, tả đủ: chủ thể + hành động + camera + ánh sáng + style chung.
  **Nhắc lại đặc điểm nhân vật** (từ `characters[].desc`) trong prompt — đừng chỉ dựa vào ảnh ref.
- **KHÔNG yêu cầu chữ trong hình** (sub burn sau khi ráp). `flowgen scene-images` TỰ nối
  "no text, no watermark…" vào prompt (AI hay tự bịa chữ/thư pháp dù không yêu cầu) — tắt bằng `--allow-text`.
- **Continuity địa điểm:** cảnh liền kề CÙNG bối cảnh → lặp **nguyên văn** cụm mô tả địa điểm
  (đừng để cảnh sau đổi setting bất ngờ vì prompt không ràng buộc địa điểm với cảnh trước).
- Style chung (art style, palette, lighting) lặp NGUYÊN VĂN ở mọi prompt → các cảnh đồng bộ.
- Đổi góc nhân vật → tách cảnh mới, đặt `angle` đúng.
- 1 cảnh = 1 ý, 4-10s. Mặc định 1 chuyển động chính (1 cú); beat ĐẮT (hook/turn/payoff, thoại) →
  cân nhắc `shots[]` 2-3 cú cắt xen trong cùng lần gen (coverage — `scene-grammar.md` §6-§7).
  Cảnh không nhân vật → `mode: "t2v"`, bỏ `characters`.
- `vo` mỗi cảnh nên đọc hết trong ~`duration` giây (tiếng Việt ~3-4 chữ/giây;
  cảnh 8s ≈ 24-30 chữ). Lệch nhiều thì khi ráp clip bị kéo/nén quá tay.
- **`vo` PHẢI đủ dấu tiếng Việt** — TTS (consumer ở Stage 4) đọc nguyên văn field này; viết không dấu
  ("nam ay toi") → giọng đọc SAI hoàn toàn. JSON là UTF-8 nên dấu an toàn, đừng né sang không dấu vì sợ
  encoding. (Ranh giới producer→consumer: ràng buộc của TTS phải được giữ ngay tại lúc viết `vo`.)

## Field craft (Mức 3 — TÙY CHỌN, backward-compatible)

Các field dưới đây **không bắt buộc** — dự án cũ thiếu chúng vẫn chạy y nguyên. Khi có, script
dùng để nâng chất lượng. Nền tảng bằng chứng nằm ở các file `references/` của từng skill (đọc
trước khi điền — đã lọc số liệu bịa, chỉ giữ kỹ thuật có nguồn):

- **`hook`** (project-level) — mở đầu là nơi tụt người xem mạnh nhất: short-form quyết trong
  **~3 giây** ("swipe or stay"), long-form tụt mạnh nhất **15-30 giây** đầu (YouTube Help: intro
  đo bằng % còn xem sau 30s). Điền `promise`/`first_frame`/`spoken` để dồn lực vào đây; cảnh mở
  đặt `role: "hook"`. Chi tiết: `vidgen-script/references/hook-and-structure.md`.
- **`role`** (scene) — vai trò cảnh trong mạch kể (3 hồi, hoặc kishōtenketsu 4 phần
  ki→shō→ten→ketsu cho video KHÔNG dựa xung đột). Cho biết cảnh nào là hook (đầu tư nhất) / payoff.
- **`shot_size`** (scene) — cỡ cảnh; **đa dạng giữa các cảnh liền kề** cho nhịp thị giác. Đưa
  thẳng vào `prompt` (Veo hiểu "wide establishing shot", "medium shot", "close-up"). Đừng để mọi
  cảnh cùng một cỡ.
- **`camera_move`** (scene) — chuyển động máy có chủ đích, đưa vào `prompt` (Veo hiểu "slow
  push-in", "180-degree orbit", "handheld", "static"). Vựng từ đầy đủ:
  `vidgen-clips/references/veo-prompt-craft.md`.
- **`music.mood`** (project-level) — assemble tự chọn nhạc nền khớp mood từ `assets/bgm/`, hoặc
  `music.file` chỉ định tay. Chi tiết: `vidgen-assemble/references/caption-and-audio.md`.

## Field craft chi tiết + PROMPT COMPILER (Mức 4 — TÙY CHỌN, backward-compatible)

Mục tiêu: kịch bản **máy-đọc-được** — thay vì nhồi mọi thứ vào 1 ô `prompt` chữ tự do, tách thành
field có cấu trúc để (a) QC tự động, (b) auto-fill từ tri thức điện ảnh, (c) giữ continuity. Toàn bộ
đều **không bắt buộc**; thiếu thì hành xử y như Mức 3.

**Cách compiler làm việc** (`flowgen compile-prompts`):
`prompt` là field **DẪN XUẤT** do compiler sở hữu — muốn viết tay thì bật `prompt_override: true`.
1. `prompt_override: true` → **giữ nguyên** prompt viết tay, bỏ qua. Đây là cách DUY NHẤT để viết prompt tay.
   (Dự án Mức 3 cũ có `prompt` tay nhưng thiếu `action` → compiler cũng GIỮ, không xoá; nên set
   `prompt_override` để chốt.)
2. Ngược lại (có `action`) ghép `prompt` theo 5 khối Veo đúng thứ tự — **ghi đè**, nên đổi field rồi
   chạy lại là prompt cập nhật (idempotent: cùng field → cùng prompt):
   `[Cinematography] + [Subject] + [Action] + [Context] + [Style & Ambiance]`
   - **[Cinematography]** ← `shot_size` + `camera_angle` + `camera_move` + `lens` + `screen_direction`.
   - **[Subject]** ← `characters[].desc` (nhắc NGUYÊN VĂN) + `dialogue[]` (thoại trong ngoặc kép).
   - **[Action]** ← `action` (mô tả hành động chính bằng tiếng Anh — người viết cấp, compiler không bịa).
   - **[Context]** ← `locations[location].desc` (nhắc NGUYÊN VĂN) → khoá bối cảnh.
   - **[Style & Ambiance]** ← `style` (project) + `lighting` + `atmosphere` + `sfx[]`.
3. **Emotion auto-fill:** nếu `lighting`/`camera_angle`/`atmosphere` để trống mà có `emotion` →
   compiler điền mặc định theo bảng `references/emotion-recipe.md`. Điền tay luôn thắng.
4. **Coverage `shots[]`:** cảnh có `shots[]` → khối [Cinematography]+[Action] được thay bằng CHUỖI
   mốc thời gian `[00:00-00:03] <cỡ cảnh, góc> ... <action cú đó>. [00:03-00:06] ...` (timestamp
   prompting Veo 3.1); mỗi cú thiếu `action` = THIẾU LIỆU. [Subject]/[Context]/[Style & Ambiance]
   vẫn áp CHUNG toàn generation (nhất quán nội tại). `to` cú cuối ≤ `duration`; QC warn nếu lệch.
5. Ghi kết quả vào `scenes[].prompt`. **Idempotent** — chạy lại không nhân đôi. GATE 1B (`script_lock`) duyệt prompt đã compile — chỉ chạy compile SAU khi kịch bản đã qua GATE 1A (`story_lock`).

**Nhóm field craft chi tiết (scene):**
- **`emotion`** — cảm xúc chủ đạo; là "bộ não" auto-fill. Xem `emotion-recipe.md` để biết mỗi cảm
  xúc kéo theo góc máy / ánh sáng / cỡ cảnh / atmosphere nào.
- **`camera_angle`** — góc máy điện ảnh (eye_level/low/high/dutch/overhead/over_shoulder). ĐỪNG nhầm
  với `angle` (góc NHÂN VẬT để flowgen chọn anchor).
- **`lighting` / `atmosphere` / `lens`** — preset điện ảnh; trống thì auto theo `emotion`.
- **`sfx[]`** — hiệu ứng âm thanh named-text (vd "footsteps on gravel"). **CONSUMER** (Stage 4): assemble
  bỏ audio gốc Veo (hay lồng giọng-bịa tiếng Anh đè lời đọc), nên `sfx[]` được tiêu thụ qua đường riêng —
  `gen_sfx.py` gen file SFX sạch từ `sfx[]` → `assemble.py --sfx auto` mix làm lớp thứ 3 dưới giọng. KHÔNG mồ côi.
- **`dialogue[]`** — thoại NHÂN VẬT, tách khỏi `vo` (narration). **CÓ CONSUMER** (Stage 4, đường đa giọng): mỗi
  lượt `{char, line}` được `tts_to_ass.py` gen bằng **giọng riêng của nhân vật** (`characters[char].voice_id`),
  nối đúng timing → nghe được ở bản ráp. Prompt KHÔNG chứa câu thoại literal (chữ → AI vẽ speech
  bubble) — compiler chỉ phát tín hiệu trung tính "speaking warmly" cho khẩu hình. Xem "Đa giọng" cuối file.

**Nhóm continuity (scene) — chống 2 lỗi kinh điển của video AI ghép cảnh:**
- **`screen_direction`** — hướng chuyển động trên khung (L2R/R2L/toward/away/static). AI hay tự đảo
  hướng giữa cảnh → ghi rõ để giữ mạch (luật 180°). Chi tiết: `vidgen-clips/references/veo-prompt-craft.md`.
- **`subject_position`** + **`match_cut_with`** — nối vị trí chủ thể / match cut (2 cảnh trùng hình-thái).
- **`location`** — khoá bối cảnh: trỏ `locations[]`, compiler lặp nguyên văn desc + flowgen dùng
  location anchor. Giải bài "mỗi cảnh Veo vẽ một kiểu cùng một quán".
- **`link_prev`** — frame-chaining (đã thực thi): `flowgen scene-clips` trích khung cuối NÉT nhất
  (chọn theo Laplacian variance, chống motion-blur) của clip cảnh trước → upload → làm khung đầu cảnh
  này. Gen TUẦN TỰ theo thứ tự manifest; cần clip cảnh trước tồn tại (cùng run hoặc run trước). Cảnh
  `link_prev` không cần ảnh riêng đã duyệt. Cặp đổi bối cảnh hoàn toàn thì ĐỪNG bật (frame-chain vô nghĩa).

## Ba đường gen theo số thực thể cần neo (đồng bộ toàn diện — chất lượng trước credit)

Ngân sách reference của Veo/Flow là **3 ảnh/generation** (tài liệu Vertex AI còn ghi 3 ảnh vốn cho
MỘT chủ thể; ref và first-frame loại trừ nhau trong 1 lần gen). Workflow v2: đơn vị gen là **SHOT**
(cảnh 1 cú = 1 shot) — chọn đường cho TỪNG shot:

| Shot | Đường gen | Cơ chế neo |
|---|---|---|
| Thường (≤2 nhân vật mặt rõ + location) | **i2v từ ảnh khung đầu ĐÃ DUYỆT** (mặc định pipeline) | ảnh gen với ≤3 anchor ref, người duyệt khung |
| Shot con trong cảnh ≥2 shot | **derive từ master**: ảnh khung đầu gen với ref = frame MASTER + anchor nhân vật | master truyền không gian/ánh sáng; danh tính từ anchor gốc |
| Micro-cut timestamp (style 2) | **r2v + anchor** (đã kiểm chứng nội bộ cảnh 9) | ≤3 ref: nhân vật > prop hero > location |
| Đông thực thể (>3 ứng viên neo) | **composite first-frame** (`flowgen compose-frame`) | ghép DẦN từng thực thể vào 1 khung bằng edit ảnh miễn phí (mỗi lượt ≤3 ref, tích lũy), duyệt khung, rồi i2v |

- Thứ tự ưu tiên slot khi phải cắt: **nhân vật mặt rõ → ref_prev (frame cảnh trước) → hero-prop →
  location anchor** (ref_prev có mặt thì location anchor NHƯỜNG — frame thật chứa không gian rồi).
- 2 luật an toàn khi dùng ảnh cảnh trước (link_prev / ref_prev): ① danh tính nhân vật LUÔN từ anchor
  gốc, frame trước chỉ mang vai không gian/ánh sáng (chống trôi photocopy qua nhiều đời);
  ② chỉ chain/ref từ clip đã qua `flowgen qc-clips` (chống lỗi AI-tell lây lan).
- MỌI cảnh đường i2v/composite: khung đầu PHẢI người duyệt trước khi đốt credit (kể cả khung
  chain — `flowgen extract-chain` trích trước để duyệt, scene-clips dùng lại file đã duyệt).

## Đa giọng — "vừa kể vừa đối thoại" (lồng tiếng, ĐÃ thực thi)

Pipeline dựng được video vừa có **người kể** (narration) vừa có **nhân vật nói chuyện thật** — mỗi
người một giọng ElevenLabs. Kiểu **lồng tiếng (dub)**: giọng đúng nhân vật + nội dung tiếng Việt kiểm
soát được, **KHÔNG khớp miệng** (ta bỏ audio gốc Veo nên clip không có cử động miệng khớp từng từ).

**Cách khai báo:**
1. `voice_id` (project-level) = giọng **narrator** (đọc `vo`).
2. `characters[].voice_id` = giọng **riêng từng nhân vật** (đọc `dialogue[]`). Thiếu → fallback narrator.
3. **Mô hình P1 — mỗi cảnh 1 kiểu tiếng:** cảnh HOẶC có `vo` (kể) HOẶC có `dialogue[]` (thoại). Muốn
   đan xen kể–thoại thì **tách cảnh** (cảnh kể riêng, cảnh thoại riêng) — vừa hợp nhịp cắt, vừa cho
   phép **cắt sang người nghe/góc lưng** khi ai đó nói (giấu chỗ lệch miệng). Một cảnh `dialogue[]`
   chứa **1-3 lượt** được (khi khung đủ rộng, miệng nhỏ khó soi); mặc định nên 1 lượt/cảnh.

**Cơ chế consumer** (`tts_to_ass.py`, tự kích hoạt khi manifest có `dialogue[]`):
- Gen TTS **từng cảnh đúng giọng** → nối lại (chèn khoảng lặng `--gap` mặc định 0.25s giữa các lượt/cảnh
  cho nhịp thở) → `narration.mp3`. Mốc `timings.json` đo từ **độ dài audio thật** (ffprobe) nên khớp
  chính xác. `subs.ass` gom dòng **riêng theo từng lượt** (không lẫn giọng). **Sub KHÔNG gắn tên người
  nói** — giọng khác nhau đã đủ phân biệt.
- **Hybrid, backward-compat:** manifest **không có** `dialogue[]` → chạy y nguyên đường 1-lệnh cũ
  (narrator thuần, prosody mượt, rẻ hơn). Chỉ khi có `dialogue[]` mới rẽ per-scene.
- **Hợp đồng với `assemble.py` KHÔNG đổi:** vẫn tiêu thụ đúng 3 file `narration.mp3` + `timings.json` +
  `subs.ass`. Không phải sửa assemble.
- **Âm dương:** hội thoại qua-lại nhanh = nhiều cảnh = nhiều clip = tốn credit hơn. Cân nhắc mật độ thoại.
- Cách VIẾT thoại lồng tiếng cho tự nhiên (thoại khi không cận mặt chính diện...): xem
  `vidgen-script/references/vo-writing-craft.md` mục "Viết thoại kiểu lồng tiếng".
