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
  durationInFrames: number; // TỔNG = nội dung + end-card (đã cộng thêm)
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

// ── INTRO: logo loang màu nước (bloom) → co nhỏ, trượt về góc trên–trái ─────────
// Nội dung/lời đọc đã chạy từ giây 0 (bg). Logo chỉ là lớp trồi lên rồi LẮNG vào watermark.
const IntroLogo: React.FC<{ src: string }> = ({ src }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const bloomIn = 0.5 * fps;
  const hold = 1.2 * fps;
  const settle = 1.7 * fps;

  const opacity = interpolate(frame, [0, bloomIn, hold, settle], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: BEZIER,
  });
  const scale = interpolate(frame, [0, bloomIn, settle], [0.62, 1, 0.72], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: BEZIER,
  });
  const blur = interpolate(frame, [0, bloomIn], [22, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const tx = interpolate(frame, [hold, settle], [0, -0.24], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: BEZIER,
  });
  const ty = interpolate(frame, [hold, settle], [0, -0.28], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: BEZIER,
  });
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
      <Img
        src={staticFile(src)}
        style={{
          width: "52%",
          opacity,
          filter: `blur(${blur}px)`,
          transform: `translate(${tx * 100}%, ${ty * 100}%) scale(${scale})`,
        }}
      />
    </AbsoluteFill>
  );
};

// ── WATERMARK: biểu tượng mờ, tĩnh, góc trên–trái, suốt phần nội dung ───────────
const Watermark: React.FC<{ src: string }> = ({ src }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const opacity = interpolate(frame, [0, 0.5 * fps], [0, 0.42], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: BEZIER,
  });
  return (
    <AbsoluteFill style={{ justifyContent: "flex-start", alignItems: "flex-start" }}>
      <Img src={staticFile(src)} style={{ width: "13%", opacity, margin: "3.5% 0 0 4%" }} />
    </AbsoluteFill>
  );
};

// ── Chân end-card dùng chung: tagline + wordmark + url (mốc giây tuỳ template) ───
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
    <>
      <div
        style={{
          opacity: fadeAt(frame, fps, t),
          transform: `translateY(${riseAt(frame, fps, t)}px)`,
          maxWidth: "80%",
          marginTop: "3%",
          textAlign: "center",
          fontFamily: FONT,
          fontWeight: 700,
          fontSize: "clamp(30px, 4.4vw, 64px)",
          lineHeight: 1.25,
          color,
        }}
      >
        {tagline}
      </div>
      <div
        style={{
          opacity: fadeAt(frame, fps, t + 0.5),
          transform: `translateY(${riseAt(frame, fps, t + 0.5)}px)`,
          marginTop: "auto",
          textAlign: "center",
          fontFamily: FONT,
          fontWeight: 700,
          fontSize: "clamp(44px, 6.6vw, 104px)",
          color,
        }}
      >
        {brandName}
      </div>
      <div
        style={{
          opacity: fadeAt(frame, fps, t + 0.8) * 0.85,
          transform: `translateY(${riseAt(frame, fps, t + 0.8)}px)`,
          marginBottom: "12%",
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
    </>
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
        justifyContent: "flex-start",
        alignItems: "center",
      }}
    >
      <div
        style={{
          width: "100%",
          height: "60%",
          marginTop: "6%",
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
      <BrandFooter tagline={p.tagline} brandName={p.brandName} ctaUrl={p.ctaUrl} color={p.color} t={1.0} />
    </AbsoluteFill>
  );
};

export const VidgenOverlay: React.FC<VidgenOverlayProps> = (props) => {
  const { fps } = useVideoConfig();
  const content = props.contentDurationInFrames;
  const wmStart = Math.round(1.5 * fps);

  return (
    <AbsoluteFill style={{ backgroundColor: props.colorBgTop }}>
      <FontFace file={props.fontFile} />

      {/* Nền: bản final ffmpeg (giọng + sub + nhạc). Chỉ phủ phần NỘI DUNG. */}
      <Sequence from={0} durationInFrames={content} layout="none">
        <Video src={staticFile(props.bg)} />
      </Sequence>

      {/* Intro logo bloom → lắng vào watermark (chỉ trong phần nội dung) */}
      <Sequence from={0} durationInFrames={content} layout="none">
        <IntroLogo src={props.logoLockup} />
      </Sequence>

      {/* Watermark tĩnh: hiện sau khi intro lắng (~1.5s) tới hết nội dung */}
      <Sequence from={wmStart} durationInFrames={Math.max(1, content - wmStart)} layout="none">
        <Watermark src={props.logoMark} />
      </Sequence>

      {/* END-CARD: cộng thêm ở cuối (nền brand + hero nở + wordmark + url) */}
      <Sequence from={content} durationInFrames={props.endCardDurationInFrames} layout="none">
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

      {/* Âm thanh — nốt chuông intro (duck dưới lời, vol thấp) */}
      {props.sonicFile ? (
        <Sequence from={0} layout="none">
          <Audio src={staticFile(props.sonicFile)} volume={0.28} />
        </Sequence>
      ) : null}

      {/* Lời CTA cuối — bg đã hết nên phát sạch */}
      {props.ctaVoiceFile ? (
        <Sequence from={content + Math.round(0.25 * fps)} layout="none">
          <Audio src={staticFile(props.ctaVoiceFile)} />
        </Sequence>
      ) : null}

      {/* Nốt chuông đóng khung — ngân gần cuối end-card, không chồng lời */}
      {props.sonicFile ? (
        <Sequence from={content + props.endCardDurationInFrames - Math.round(1.0 * fps)} layout="none">
          <Audio src={staticFile(props.sonicFile)} volume={0.5} />
        </Sequence>
      ) : null}
    </AbsoluteFill>
  );
};
