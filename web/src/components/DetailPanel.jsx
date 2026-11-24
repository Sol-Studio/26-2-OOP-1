import { useFarm } from "../lib/farm.jsx";
import { signedWon, won } from "../lib/format.js";
import ChartGrid from "./ChartGrid.jsx";
import DeviceControls from "./DeviceControls.jsx";
import GrowthTimeline from "./GrowthTimeline.jsx";
import { Card } from "./ui.jsx";

/** 선택한 구역의 장치(상태·수동 제어), 생육 단계, 24시간 그래프, 이번 재배 비용 */
export default function DetailPanel() {
  const { state, selected } = useFarm();
  const s = state.sections[selected];
  const d = s.devices;

  return (
    <Card
      title={`${s.label} 상세`}
      aside={`누적 물 ${Math.round(d.totalWater)}L · 비료 ${Math.round(d.totalFertilizer)}g · 전력 ${d.totalKwh.toFixed(1)}kWh (현재 ${d.powerKw.toFixed(1)}kW)`}
    >
      <DeviceControls section={s} />
      <GrowthTimeline section={s} />
      <ChartGrid section={s} />
      <MoneyPanel section={s} />
    </Card>
  );
}

function MoneyPanel({ section: s }) {
  const { items, cost, expected, price } = s.money;
  const net = expected == null ? null : expected - cost;
  return (
    <div className="mt-4 rounded-lg bg-pressed p-3.5">
      <div className="flex items-baseline justify-between">
        <h3 className="text-sm font-bold">이번 재배 비용</h3>
        <span className="tabular text-sm font-bold">{won(cost)}</span>
      </div>
      <dl className="mt-2 grid grid-cols-4 gap-2 text-xs">
        {items.map(([name, v]) => (
          <div key={name}>
            <dt className="text-muted">{name}</dt>
            <dd className="tabular font-mono">{won(v)}</dd>
          </div>
        ))}
      </dl>
      <div className="mt-3 flex items-baseline justify-between border-t border-line pt-2.5 text-sm">
        {expected == null ? (
          <span className="text-muted">예상 수익 없음</span>
        ) : (
          <>
            <span className="text-muted">
              예상 수익 {won(expected)} <span className="text-xs">· 현재 시세 {won(price)}/kg</span>
            </span>
            <span className={`tabular font-bold ${net >= 0 ? "text-positive" : "text-critical"}`}>순이익 {signedWon(net)}</span>
          </>
        )}
      </div>
    </div>
  );
}
