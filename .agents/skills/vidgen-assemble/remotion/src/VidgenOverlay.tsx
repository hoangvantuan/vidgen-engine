import {
  AbsoluteFill,
  Img,
  Sequence,
  Easing,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
  staticFile,
} from "remotion";
import { Audio, Video } from "@remotion/media";

// Engine GENERIC: mọi giá trị brand (màu, tên, url, asset, template) đến từ PROPS.
// Preset brand nằm ở assets/brands/<tên>/brand.json — apply_brand.py nạp vào props.
export type VidgenOverlayProps = {
  bg: string; // final.mp4 (đã có sub/nhạc/giọng) — Python copy vào public/bg.mp4
  durationInFrames: number; // TỔNG = intro + nội dung + end-card (đã cộng thêm)
  introDurationInFrames: number; // intro logo ĐỨNG RIÊNG ở đầu (0 = tắt intro)
  contentDurationInFrames: number; // độ dài bản final nội dung (bg.mp4)
  endCardDurationInFrames: number; // phần end-card CỘNG THÊM ở cuối
  fps: number;
  width: number;
  height: number;
  endcardTagline: string; // ô BIẾN THIÊN theo phẩm chất (fallback trung tính lo ở Python)
  brandName: string; // wordmark, vd "Your Brand"
  ctaUrl: string; // vd "yourbrand.com"
  colorBgTop: string; // nền end-card (trên)
  colorBgBottom: string; // nền end-card (dưới)
  colorText: string; // màu chữ end-card
  logoLockup: string; // public/ — logo đầy đủ (bloom đầu video, template logo_reveal)
  logoMark: string; // public/ — chỉ biểu tượng (watermark góc)
  heroImg: string; // public/ — ảnh hero end-card (template tree_grow); rỗng nếu template khác
  heroAspect: string; // tỉ lệ ảnh hero cho clip đúng, vd "2048 / 2006"
  fontFile: string; // font tiếng Việt trong public/ (Be Vietnam Pro)
  sonicFile: string; // nốt chuông mềm (rỗng = bỏ)
  ctaVoiceFile: string; // lời đọc CTA cuối (rỗng = bỏ)
};

const BEZIER = Easing.bezier(0.16, 1, 0.3, 1);

// @font-face nội tuyến để giữ dấu tiếng Việt khi render offline (font bundle trong public/).
const FontFace: React.FC<{ file: string }> = ({ file }) => (
  <style>{`@font-face{font-family:'VidgenVN';src:url(${staticFile(file)});font-weight:700;}`}</style>
);
const FONT = "'VidgenVN', 'Be Vietnam Pro', system-ui, sans-serif";

const fadeAt = (frame: number, fps: number, startSec: number) =>
  interpolate(frame, [startSec * fps, (startSec + 0.5) * fps], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: BEZIER,
  });
const riseAt = (frame: number, fps: number, startSec: number) =>
  interpolate(frame, [startSec * fps, (startSec + 0.6) * fps], [22, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: BEZIER,
  });

// ── INTRO ĐỨNG RIÊNG: logo loang màu nước (bloom) trên NỀN GRADIENT BRAND ────────
// KHÔNG đè lên cảnh. Chiếm [0, intro+fade]: giây cuối cả nền lẫn logo mờ 1→0 để
// cảnh chính (chạy bên dưới từ mốc `intro`) lộ ra — bàn giao "fade qua màu nền".
const IntroSegment: React.FC<{
  src: string;
  introFrames: number;
  fadeFrames: number;
  colorBgTop: string;
  colorBgBottom: string;
}> = ({ src, introFrames, fadeFrames, colorBgTop, colorBgBottom }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const bloomIn = 0.5 * fps;
  const logoOut = introFrames - 0.35 * fps; // logo tắt TRƯỚC khi nền wash mờ đi

  // Logo: loang nét dần rồi giữ, tắt hẳn trước mốc `intro`.
  const logoOpacity = interpolate(
    frame,
    [0, bloomIn, logoOut, introFrames],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: BEZIER },
  );
  const scale = interpolate(frame, [0, bloomIn, introFrames], [0.62, 1, 1.05], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: BEZIER,
  });
  const blur = interpolate(frame, [0, bloomIn], [22, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  // Nền gradient: mờ 1→0 ở đúng `fadeFrames` cuối → cảnh bên dưới lộ ra (crossfade).
  const bgOpacity = interpolate(
    frame,
    [introFrames, introFrames + fadeFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: BEZIER },
  );
  return (
    <AbsoluteFill
      style={{
        opacity: bgOpacity,
        background: `linear-gradient(180deg, ${colorBgTop} 0%, ${colorBgBottom} 100%)`,
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      <Img
        src={staticFile(src)}
        style={{
          width: "52%",
          opacity: logoOpacity,
          filter: `blur(${blur}px)`,
          transform: `scale(${scale})`,
        }}
      />
    </AbsoluteFill>
  );
};

// ── Chân end-card: tagline → gạch phân cách mảnh → wordmark → url, GOM thành CỤM ──
// Bố cục PACKED (bỏ marginTop:auto vốn tách wordmark xuống đáy gây "hố trống" giữa).
// Cả cụm căn giữa dọc trong EndCard → nhịp cân đối, không khoảng cream rỗng.
const BrandFooter: React.FC<{
  tagline: string;
  brandName: string;
  ctaUrl: string;
  color: string;
  t: number; // giây bắt đầu tagline
}> = ({ tagline, brandName, ctaUrl, color, t }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        width: "100%",
        marginTop: "5%",
      }}
    >
      <div
        style={{
          opacity: fadeAt(frame, fps, t),
          transform: `translateY(${riseAt(frame, fps, t)}px)`,
          maxWidth: "82%",
          textAlign: "center",
          fontFamily: FONT,
          fontWeight: 700,
          fontSize: "clamp(30px, 4.6vw, 66px)",
          lineHeight: 1.28,
          color,
        }}
      >
        {tagline}
      </div>
      {/* Gạch phân cách mảnh — tạo nhịp + cảm giác premium, lấp khoảng trống giữa */}
      <div
        style={{
          opacity: fadeAt(frame, fps, t + 0.35) * 0.5,
          width: "clamp(72px, 12vw, 168px)",
          height: 3,
          borderRadius: 3,
          marginTop: "5.5%",
          background: color,
        }}
      />
      <div
        style={{
          opacity: fadeAt(frame, fps, t + 0.5),
          transform: `translateY(${riseAt(frame, fps, t + 0.5)}px)`,
          marginTop: "5.5%",
          textAlign: "center",
          fontFamily: FONT,
          fontWeight: 700,
          fontSize: "clamp(46px, 6.8vw, 108px)",
          lineHeight: 1.05,
          color,
        }}
      >
        {brandName}
      </div>
      <div
        style={{
          opacity: fadeAt(frame, fps, t + 0.75) * 0.85,
          transform: `translateY(${riseAt(frame, fps, t + 0.75)}px)`,
          marginTop: "1.8%",
          textAlign: "center",
          fontFamily: FONT,
          fontWeight: 700,
          fontSize: "clamp(28px, 4vw, 60px)",
          letterSpacing: "0.02em",
          color,
        }}
      >
        {ctaUrl}
      </div>
    </div>
  );
};

type EndCardProps = {
  tagline: string;
  brandName: string;
  ctaUrl: string;
  color: string;
  heroImg: string;
  heroAspect: string;
};

// ── END-CARD: nền brand + ảnh hero NẢY NỞ (reveal mask từ gốc lên) + wordmark + url ─
// Mọi giá trị (màu, hero, wordmark, url) từ props/preset — không brand nào hardcode.
const EndCard: React.FC<
  EndCardProps & { colorBgTop: string; colorBgBottom: string }
> = ({ colorBgTop, colorBgBottom, ...p }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const bgOpacity = interpolate(frame, [0, 0.4 * fps], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: BEZIER,
  });
  const grow = interpolate(frame, [0.2 * fps, 1.5 * fps], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: BEZIER,
  });
  const reveal = (1 - grow) * 100; // clip từ dưới lên: hero nở từ gốc
  const scale = interpolate(grow, [0, 1], [0.92, 1]);
  return (
    <AbsoluteFill
      style={{
        opacity: bgOpacity,
        background: `linear-gradient(180deg, ${colorBgTop} 0%, ${colorBgBottom} 100%)`,
        flexDirection: "column",
        justifyContent: "center", // cả cụm (hero + chữ) căn giữa dọc → hết "hố trống"
        alignItems: "center",
        paddingBottom: "2%",
      }}
    >
      <div
        style={{
          width: "100%",
          height: "50%",
          display: "flex",
          justifyContent: "center",
          alignItems: "flex-end",
        }}
      >
        {/* Clip trên WRAPPER đúng tỉ lệ ảnh (tránh objectFit letterbox cắt nhầm vùng rỗng). */}
        <div
          style={{
            height: "100%",
            aspectRatio: p.heroAspect,
            maxWidth: "84%",
            overflow: "hidden",
            transform: `scale(${scale})`,
            transformOrigin: "bottom center",
            clipPath: `inset(${reveal}% 0% 0% 0%)`,
          }}
        >
          <Img src={staticFile(p.heroImg)} style={{ width: "100%", height: "100%", display: "block" }} />
        </div>
      </div>
      <BrandFooter tagline={p.tagline} brandName={p.brandName} ctaUrl={p.ctaUrl} color={p.color} t={0.9} />
    </AbsoluteFill>
  );
};

export const VidgenOverlay: React.FC<VidgenOverlayProps> = (props) => {
  const { fps } = useVideoConfig();
  const intro = props.introDurationInFrames; // 0 = tắt intro (bg về mốc 0)
  const content = props.contentDurationInFrames;
  const fade = Math.round(0.3 * fps); // handoff crossfade intro→cảnh chính
  const contentStart = intro; // cảnh chính bắt đầu SAU khi intro chạy trọn
  const endCardStart = intro + content;

  return (
    <AbsoluteFill style={{ backgroundColor: props.colorBgTop }}>
      <FontFace file={props.fontFile} />

      {/* Nền: bản final ffmpeg (giọng + sub + nhạc). Bắt đầu SAU intro, không đè. */}
      <Sequence from={contentStart} durationInFrames={content} layout="none">
        <Video src={staticFile(props.bg)} />
      </Sequence>

      {/* INTRO ĐỨNG RIÊNG: logo bloom trên nền gradient; giây cuối fade lộ cảnh chính */}
      {intro > 0 ? (
        <Sequence from={0} durationInFrames={intro + fade} layout="none">
          <IntroSegment
            src={props.logoLockup}
            introFrames={intro}
            fadeFrames={fade}
            colorBgTop={props.colorBgTop}
            colorBgBottom={props.colorBgBottom}
          />
        </Sequence>
      ) : null}

      {/* END-CARD: cộng thêm ở cuối (nền brand + hero nở + wordmark + url) */}
      <Sequence from={endCardStart} durationInFrames={props.endCardDurationInFrames} layout="none">
        <EndCard
          tagline={props.endcardTagline}
          brandName={props.brandName}
          ctaUrl={props.ctaUrl}
          color={props.colorText}
          colorBgTop={props.colorBgTop}
          colorBgBottom={props.colorBgBottom}
          heroImg={props.heroImg}
          heroAspect={props.heroAspect}
        />
      </Sequence>

      {/* Âm thanh — nốt chuông intro: ngân ngay đầu, trên nền intro (không đè lời) */}
      {props.sonicFile ? (
        <Sequence from={0} layout="none">
          <Audio src={staticFile(props.sonicFile)} volume={0.4} />
        </Sequence>
      ) : null}

      {/* Lời CTA cuối — bg đã hết nên phát sạch */}
      {props.ctaVoiceFile ? (
        <Sequence from={endCardStart + Math.round(0.25 * fps)} layout="none">
          <Audio src={staticFile(props.ctaVoiceFile)} />
        </Sequence>
      ) : null}

      {/* Nốt chuông đóng khung — ngân gần cuối end-card, không chồng lời */}
      {props.sonicFile ? (
        <Sequence from={endCardStart + props.endCardDurationInFrames - Math.round(1.0 * fps)} layout="none">
          <Audio src={staticFile(props.sonicFile)} volume={0.5} />
        </Sequence>
      ) : null}
    </AbsoluteFill>
  );
};
