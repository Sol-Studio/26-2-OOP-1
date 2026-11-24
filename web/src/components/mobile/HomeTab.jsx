import { useFarm } from "../../lib/farm.jsx";
import { TONE_BG, TONE_TEXT, won } from "../../lib/format.js";
import { Bar } from "../ui.jsx";
import { MobileHeader } from "./MobileApp.jsx";

/** 홈: 요약 칩, 정산 요약, 구역 목록 (누르면 구역 탭으로) */
export default function HomeTab({ go }) {
  const { state, selected, select } = useFarm();
  const { weather: w, sections, totals } = state;
  const ready = sections.filter((s) => s.status.label === "수확 가능").length;
  const alert = sections.filter((s) => ["critical", "dead"].includes(s.status.tone)).length;

  return (
    <>
      <MobileHeader title="우리 농장" sub={`Day ${state.day} · 바깥 ${w.temperature.toFixed(1)}°C ${w.sky} · 습도 ${Math.round(w.humidity)}%`} />

      <div className="grid grid-cols-3 gap-2">
        {[
          ["수확 가능", ready, "text-ready"],
          ["주의", alert, "text-critical"],
          ["전체 구역", sections.length, "text-positive"],
        ].map(([name, n, color]) => (
          <div key={name} className="rounded-xl bg-card p-3 ring-1 ring-line">
            <p className="text-xs text-muted">{name}</p>
            <p className={`text-xl font-bold ${color}`}>{n}</p>
          </div>
        ))}
      </div>

      <div className="mt-2 grid grid-cols-3 rounded-xl bg-card p-3 ring-1 ring-line">
        {[
          ["매출", totals.revenue, "text-ink"],
          ["비용", totals.cost, "text-ink"],
          ["순이익", totals.profit, totals.profit >= 0 ? "text-positive" : "text-critical"],
        ].map(([name, v, color]) => (
          <div key={name} className="min-w-0">
            <p className="text-xs text-muted">{name}</p>
            <p className={`tabular truncate text-sm font-bold ${color}`}>{won(v)}</p>
          </div>
        ))}
      </div>

      <ul className="mt-3 space-y-2">
        {sections.map((s) => (
          <li key={s.index}>
            <button
              onClick={() => {
                select(s.index);
                go("zone");
              }}
              className={`relative w-full overflow-hidden rounded-xl bg-card py-3 pl-5 pr-4 text-left ${
                s.index === selected ? "ring-2 ring-brand" : "ring-1 ring-line"
              }`}
            >
              <span className={`absolute inset-y-0 left-0 w-1.5 ${TONE_BG[s.status.tone]}`} />
              <div className="flex items-baseline justify-between">
                <span className="text-sm font-bold">{s.label}</span>
                <span className={`text-xs font-bold ${TONE_TEXT[s.status.tone]}`}>{s.status.label} ›</span>
              </div>
              {s.plant ? (
                <div className="mt-2 flex items-center gap-3 text-xs text-muted">
                  <span className="tabular font-mono">
                    {s.env[0].toFixed(1)}° {Math.round(s.env[1])}%
                  </span>
                  <Bar value={s.plant.growth} color={s.plant.ready ? "bg-ready" : "bg-brand"} className="h-1.5 flex-1" />
                  <span className="tabular w-8 text-right font-mono">{Math.round(s.plant.growth)}%</span>
                </div>
              ) : (
                <p className="mt-2 text-xs text-muted">비어 있음</p>
              )}
            </button>
          </li>
        ))}
      </ul>
    </>
  );
}
