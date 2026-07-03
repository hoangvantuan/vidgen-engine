import { Composition, CalculateMetadataFunction } from "remotion";
import { VidgenOverlay, VidgenOverlayProps } from "./VidgenOverlay";

// Duration/kích thước lấy từ props (Python đo bằng ffprobe rồi truyền qua --props).
const calculateMetadata: CalculateMetadataFunction<VidgenOverlayProps> = ({ props }) => {
  return {
    durationInFrames: Math.max(1, Math.round(props.durationInFrames)),
    width: props.width,
    height: props.height,
    fps: props.fps,
    props,
  };
};

export const RemotionRoot = () => {
  return (
    <Composition
      id="VidgenOverlay"
      component={VidgenOverlay}
      fps={30}
      width={1080}
      height={1920}
      durationInFrames={300}
      defaultProps={{
        bg: "bg.mp4",
        durationInFrames: 300,
        fps: 30,
        width: 1080,
        height: 1920,
        hookText: "",
        endCardText: "",
        titleDurationInFrames: 90,
        endCardDurationInFrames: 90,
        fontFile: "BeVietnamPro-Bold.ttf",
      }}
      calculateMetadata={calculateMetadata}
    />
  );
};
