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
      durationInFrames={390}
      defaultProps={{
        bg: "bg.mp4",
        durationInFrames: 390,
        contentDurationInFrames: 300,
        endCardDurationInFrames: 90,
        fps: 30,
        width: 1080,
        height: 1920,
        endcardTagline: "Tagline mẫu của brand.",
        brandName: "Your Brand",
        ctaUrl: "yourbrand.com",
        colorBgTop: "#FDF6EC",
        colorBgBottom: "#FBE4D2",
        colorText: "#3E5A87",
        logoLockup: "logo_lockup.png",
        logoMark: "logo_mark.png",
        heroImg: "hero.png",
        heroAspect: "2048 / 2006",
        fontFile: "BeVietnamPro-Bold.ttf",
        sonicFile: "",
        ctaVoiceFile: "",
      }}
      calculateMetadata={calculateMetadata}
    />
  );
};
