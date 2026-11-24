import { useFarm } from "../lib/farm.jsx";
import { TONE_TEXT, healthBg } from "../lib/format.js";
import { Bar } from "./ui.jsx";

/** 구역 카드 6장: 상태, 작물과 생육 단계, 건강·생장 막대만 간단히 (환경 값·장치는 상세 패널에서) */
export default function SectionCards() {
  const { state, selected, select } = useFarm();
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
      {state.sections.map((s) => {
        const ps = s.plant;
        const sel = s.index === selected;
        const bg = s.closed ? "bg-critical-weak" : !ps ? "bg-pressed" : !ps.alive ? "bg-dead-bg" : "bg-card";
        return (
          <button
            key={s.index}
            onClick={() => select(s.index)}
            aria-pressed={sel}
            className={`rounded-xl p-3.5 text-left transition-shadow ${bg} ${
              sel ? "ring-2 ring-brand" : "ring-1 ring-line hover:ring-subtle"
            }`}
          >
            <div className="flex items-baseline justify-between gap-2">
              <span className="truncate text-sm font-bold text-ink">{s.label}</span>
              <span className={`shrink-0 text-xs font-bold ${TONE_TEXT[s.status.tone]}`}>{s.status.label}</span>
            </div>
            {ps ? (
              <>
                <p className="mt-3 text-xs text-muted">생육 단계</p>
                <p className="text-lg font-bold text-ink">{ps.stage}</p>
                <Meter name="건강" value={ps.health} color={healthBg(ps.health)} />
                <Meter name="생장" value={ps.growth} color={ps.ready ? "bg-ready" : "bg-brand"} />
              </>
            ) : (
              <p className="py-6 text-center text-sm text-muted">비어 있음 · 작물을 골라 심기</p>
            )}
          </button>
        );
      })}
    </div>
  );
}

function Meter({ name, value, color }) {
  return (
    <div className="mt-2 flex items-center gap-2 text-xs">
      <span className="w-7 text-muted">{name}</span>
      <Bar value={value} color={color} className="h-1.5 flex-1" />
      <span className="tabular w-9 text-right font-mono text-ink">{Math.round(value)}%</span>
    </div>
  );
}
