import {
  AbsoluteFill,
  Sequence,
  Easing,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
  staticFile,
} from "remotion";
import { Video } from "@remotion/media";

export type VidgenOverlayProps = {
  bg: string; // file trong public/ (Python copy final.mp4 → public/bg.mp4)
  durationInFrames: number;
  fps: number;
  width: number;
  height: number;
  hookText: string; // câu hook/title hiện ở đầu (tiếng Việt)
  endCardText: string; // brand/CTA cuối
  titleDurationInFrames: number;
  endCardDurationInFrames: number;
  fontFile: string; // font tiếng Việt trong public/ (Be Vietnam Pro)
};

// @font-face nội tuyến để giữ dấu tiếng Việt khi render offline (font bundle trong public/).
const FontFace: React.FC<{ file: string }> = ({ file }) => (
  <style>{`@font-face{font-family:'VidgenVN';src:url(${staticFile(file)});font-weight:700;}`}</style>
);

const FONT = "'VidgenVN', 'Be Vietnam Pro', system-ui, sans-serif";

// Title/hook: fade + scale vào rồi mờ ra ở đầu video.
const TitleCard: React.FC<{ text: string }> = ({ text }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const inEnd = Math.min(0.6 * fps, durationInFrames / 3);
  const outStart = durationInFrames - Math.min(0.5 * fps, durationInFrames / 3);
  const opacity = interpolate(
    frame,
    [0, inEnd, outStart, durationInFrames],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.bezier(0.16, 1, 0.3, 1) },
  );
  const scale = interpolate(frame, [0, inEnd], [0.92, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });
  return (
    <AbsoluteFill style={{ justifyContent: "flex-start", alignItems: "center", paddingTop: "12%" }}>
      <div
        style={{
          opacity,
          scale,
          maxWidth: "82%",
          textAlign: "center",
          fontFamily: FONT,
          fontWeight: 700,
          fontSize: "clamp(40px, 6vw, 96px)",
          lineHeight: 1.12,
          color: "white",
          textShadow: "0 4px 24px rgba(0,0,0,0.65)",
          padding: "0.4em 0.7em",
          borderRadius: 18,
          background: "rgba(0,0,0,0.28)",
        }}
      >
        {text}
      </div>
    </AbsoluteFill>
  );
};

// End-card: nền tối fade vào + brand/CTA.
const EndCard: React.FC<{ text: string }> = ({ text }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const opacity = interpolate(frame, [0, 0.5 * fps], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });
  const y = interpolate(frame, [0, 0.6 * fps], [24, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });
  return (
    <AbsoluteFill style={{ backgroundColor: `rgba(0,0,0,${0.72 * opacity})` }}>
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
        <div
          style={{
            opacity,
            translate: `0px ${y}px`,
            maxWidth: "80%",
            textAlign: "center",
            fontFamily: FONT,
            fontWeight: 700,
            fontSize: "clamp(44px, 6.5vw, 104px)",
            lineHeight: 1.15,
            color: "white",
          }}
        >
          {text}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

export const VidgenOverlay: React.FC<VidgenOverlayProps> = (props) => {
  const { durationInFrames } = useVideoConfig();
  const endFrom = Math.max(0, durationInFrames - props.endCardDurationInFrames);
  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      <FontFace file={props.fontFile} />
      {/* Nền: bản final.mp4 do ffmpeg ráp (đã có sub/nhạc) */}
      <Video src={staticFile(props.bg)} />
      {/* Title/hook đầu video */}
      {props.hookText ? (
        <Sequence from={0} durationInFrames={props.titleDurationInFrames} layout="none">
          <TitleCard text={props.hookText} />
        </Sequence>
      ) : null}
      {/* End-card cuối video */}
      {props.endCardText ? (
        <Sequence from={endFrom} durationInFrames={props.endCardDurationInFrames} layout="none">
          <EndCard text={props.endCardText} />
        </Sequence>
      ) : null}
    </AbsoluteFill>
  );
};
