import { useEffect, useRef, useState } from "react";
import Greenhouse from "./Greenhouse.jsx";
import SectionCards from "./SectionCards.jsx";
import ControlBar from "./ControlBar.jsx";
import DetailPanel from "./DetailPanel.jsx";
import HarvestLog from "./HarvestLog.jsx";
import LogPanel from "./LogPanel.jsx";

const SHRINK = "top 0.8s cubic-bezier(.2,.8,.2,1), left 0.8s cubic-bezier(.2,.8,.2,1), width 0.8s cubic-bezier(.2,.8,.2,1), height 0.8s cubic-bezier(.2,.8,.2,1), border-radius 0.8s";

/** 관리 패널: 왼쪽은 온실 전체(3D·구역 카드·수확 기록), 오른쪽은 선택한 구역의 상세와 로그.
 *  intro면 3D CCTV가 전체 화면으로 먼저 뜨고, 카메라가 내려온 뒤 제자리(왼쪽 위 칸)로 줄어든다. */
export default function Dashboard({ intro = false, onIntroEnd }) {
  const slot = useRef(null);
  const [phase, setPhase] = useState(intro ? "full" : "done"); // full → shrink → done
  const [rect, setRect] = useState(null);

  // 3D 화면 칸은 늘 같은 요소다 (Canvas를 다시 만들지 않으려고). 연출 중에만 fixed로 띄워 크기를 바꾼다.
  let style;
  if (phase === "full") style = { position: "fixed", left: 0, top: 0, width: innerWidth, height: innerHeight, zIndex: 60, borderRadius: 0, transition: SHRINK };
  else if (phase === "shrink" && rect) style = { position: "fixed", left: rect.left, top: rect.top, width: rect.width, height: rect.height, zIndex: 60, borderRadius: 12, transition: SHRINK };

  const shrink = () => {
    const r = slot.current.getBoundingClientRect();
    setPhase("shrink");
    setRect(r);
  };
  const done = () => {
    setPhase("done");
    onIntroEnd?.();
  };
  const finish = (e) => {
    if (phase === "shrink" && e.target === e.currentTarget && e.propertyName === "width") done();
  };
  // 전환 끝 이벤트를 못 받아도(창 크기가 같았다든지) 제자리로 들어가게
  useEffect(() => {
    if (phase !== "shrink") return;
    const t = setTimeout(done, 1200);
    return () => clearTimeout(t);
  }, [phase]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)]">
      <div className="flex min-w-0 flex-col gap-4">
        <div ref={slot} className="h-[clamp(320px,46vh,520px)]">
          <div style={style} onTransitionEnd={finish} className="h-full overflow-hidden rounded-xl ring-1 ring-line">
            <Greenhouse intro={intro} onIntroDone={shrink} />
          </div>
        </div>
        <SectionCards />
        <HarvestLog />
      </div>
      <div className="flex min-w-0 flex-col gap-4">
        <ControlBar />
        <DetailPanel />
        <LogPanel />
      </div>
    </div>
  );
}
