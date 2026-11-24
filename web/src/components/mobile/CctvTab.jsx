import { useFarm } from "../../lib/farm.jsx";
import { TONE_TEXT } from "../../lib/format.js";
import Greenhouse from "../Greenhouse.jsx";
import { MobileHeader } from "./MobileApp.jsx";

/** CCTV: 선택한 구역을 3D로 가까이 보고, 아래에서 구역을 바꾼다 */
export default function CctvTab({ go }) {
  const { state, selected, select } = useFarm();
  const s = state.sections[selected];

  return (
    <>
      <MobileHeader title="CCTV" sub="구역을 누르면 그쪽으로 카메라가 갑니다" />
      <div className="aspect-[4/3] overflow-hidden rounded-xl ring-1 ring-line">
        <Greenhouse focus compact />
      </div>
      <button onClick={() => go("zone")} className="mt-2 flex w-full items-baseline justify-between py-1">
        <span className="text-sm font-bold">{s.label}</span>
        <span className={`text-xs font-bold ${TONE_TEXT[s.status.tone]}`}>{s.status.label} ›</span>
      </button>
      <div className="mt-2 grid grid-cols-3 gap-2">
        {state.sections.map((sec) => (
          <button
            key={sec.index}
            onClick={() => select(sec.index)}
            aria-pressed={sec.index === selected}
            className={`rounded-lg bg-card p-2 text-left ${sec.index === selected ? "ring-2 ring-brand" : "ring-1 ring-line"}`}
          >
            <p className="font-mono text-[10px] text-subtle">CAM {String(sec.index + 1).padStart(2, "0")}</p>
            <p className="truncate text-xs font-bold">{sec.label}</p>
            <p className={`truncate text-[11px] font-bold ${TONE_TEXT[sec.status.tone]}`}>{sec.status.label}</p>
          </button>
        ))}
      </div>
    </>
  );
}
