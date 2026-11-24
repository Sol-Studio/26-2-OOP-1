import { useFarm } from "../../lib/farm.jsx";
import { TONE_TEXT, healthBg, metricValue, signedWon, won } from "../../lib/format.js";
import DeviceControls from "../DeviceControls.jsx";
import { Bar, Button, actionBlocks } from "../ui.jsx";
import { MobileHeader } from "./MobileApp.jsx";

/** 구역 상세: 생육, 비용, 환경 값(범위를 벗어나면 빨간색), 장치 상태·수동 제어, 수확·갈아엎기 */
export default function ZoneTab({ go }) {
  const { state, meta, selected, actions } = useFarm();
  const s = state.sections[selected];
  const ps = s.plant;
  const { items, cost, expected } = s.money;
  const net = expected == null ? null : expected - cost;
  const block = actionBlocks(s);

  let info = "";
  if (ps) info = !ps.alive ? "고사" : ps.ready ? "수확 가능" : ps.daysToHarvest == null ? "계산 중" : `수확까지 ${ps.daysToHarvest.toFixed(1)}일`;

  return (
    <>
      <MobileHeader title={s.label} onBack={() => go("home")} />
      <p className={`-mt-3 mb-3 text-sm font-bold ${TONE_TEXT[s.status.tone]}`}>{s.status.label}</p>

      <div className="rounded-xl bg-card p-4 ring-1 ring-line">
        {ps ? (
          <>
            <div className="flex items-baseline justify-between">
              <span className="font-bold">{ps.stage}</span>
              <span className="text-xs text-muted">{info}</span>
            </div>
            {[
              ["생장", ps.growth, ps.ready ? "bg-ready" : "bg-brand"],
              ["건강", ps.health, healthBg(ps.health)],
            ].map(([name, v, color]) => (
              <div key={name} className="mt-2.5 flex items-center gap-3 text-xs">
                <span className="w-7 text-muted">{name}</span>
                <Bar value={v} color={color} className="h-1.5 flex-1" />
                <span className="tabular w-9 text-right font-mono">{Math.round(v)}%</span>
              </div>
            ))}
          </>
        ) : (
          <p className="py-3 text-center text-sm text-muted">빈 구역입니다. 관리 패널에서 작물을 심으세요.</p>
        )}
      </div>

      <div className="mt-2 rounded-xl bg-card p-4 ring-1 ring-line">
        <div className="flex items-start justify-between gap-2">
          <div>
            <p className="text-xs text-muted">이번 재배 비용</p>
            <p className="tabular font-bold">{won(cost)}</p>
          </div>
          {expected == null ? (
            <p className="text-xs text-muted">예상 수익 없음</p>
          ) : (
            <div className="text-right">
              <p className="text-xs text-muted">예상 수익 · 순이익</p>
              <p className={`tabular text-sm font-bold ${net >= 0 ? "text-positive" : "text-critical"}`}>
                {won(expected)} · {signedWon(net)}
              </p>
            </div>
          )}
        </div>
        <dl className="mt-3 grid grid-cols-4 gap-1 text-xs">
          {items.map(([name, v]) => (
            <div key={name}>
              <dt className="text-muted">{name}</dt>
              <dd className="tabular font-mono">{v.toLocaleString("ko-KR")}</dd>
            </div>
          ))}
        </dl>
      </div>

      <div className="mt-2 grid grid-cols-2 gap-2">
        {meta?.metrics.map((m, k) => {
          const v = s.env[k];
          const [lo, hi] = s.bands[k];
          const ok = lo <= v && v <= hi;
          return (
            <div key={m.key} className="rounded-xl bg-card p-3 ring-1 ring-line">
              <p className="flex justify-between text-xs text-muted">
                <span>{m.title}</span>
                <span className="text-[10px]">{m.unit}</span>
              </p>
              <p className={`tabular font-mono text-lg font-bold ${ok ? "text-ink" : "text-critical"}`}>
                {metricValue(v, m.range[1])}
                {!ok && <span className="ml-1 font-sans text-[10px]">범위 밖</span>}
              </p>
            </div>
          );
        })}
      </div>

      <div className="mt-2">
        <DeviceControls section={s} className="grid-cols-2" />
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2">
        <Button variant="brand" className="rounded-xl py-3 font-bold" onClick={() => actions.harvest(selected)} blocked={block.harvest}>
          {ps && !ps.alive ? "정리" : "수확"}
        </Button>
        <Button variant="solidDanger" className="rounded-xl py-3 font-bold" onClick={() => actions.plow(selected)} blocked={block.plow}>
          갈아엎기
        </Button>
      </div>
    </>
  );
}
