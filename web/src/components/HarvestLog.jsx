import { useFarm } from "../lib/farm.jsx";
import { num, signedWon, won } from "../lib/format.js";
import LedgerChart from "./LedgerChart.jsx";
import { Card } from "./ui.jsx";

/** 일별 정산 그래프, 수확 기록 표(최근 10건), 누적 매출·비용·순이익 */
export default function HarvestLog() {
  const { state } = useFarm();
  const { harvests, harvestCount, harvestKg, totals, ledger } = state;

  return (
    <Card
      data-tour="harvest"
      title="수확 기록"
      aside={`총 ${harvestCount}회 · ${harvestKg.toFixed(1)}kg · 매출 ${won(totals.revenue)} · 비용 ${won(totals.cost)} · 순이익 ${signedWon(totals.profit)}`}
    >
      <LedgerChart ledger={ledger} />
      {harvests.length === 0 ? (
        <p className="py-3 text-sm text-muted">아직 수확한 작물이 없습니다. 카드가 '수확 가능'이 되면 수확하세요.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="tabular w-full text-sm">
            <thead className="text-xs text-muted">
              <tr className="border-b border-line">
                <th className="py-1.5 text-left font-bold">일차</th>
                <th className="text-left font-bold">구역</th>
                <th className="text-left font-bold">작물</th>
                <th className="text-right font-bold">수확량</th>
                <th className="text-right font-bold">수확 시세</th>
                <th className="pl-4 text-left font-bold">품질</th>
              </tr>
            </thead>
            <tbody>
              {harvests.map((h, k) => (
                <tr key={`${harvestCount - k}`} className="border-b border-line/60 last:border-0">
                  <td className="py-1.5">Day {h.day}</td>
                  <td>{h.zone}</td>
                  <td>{h.crop}</td>
                  <td className="text-right font-mono">{h.kg.toFixed(1)} kg</td>
                  <td className="text-right font-mono">{num(h.price)}원</td>
                  <td className="pl-4">
                    <div className="flex items-center gap-2">
                      <span className="w-9 font-mono">{Math.round(h.quality)}%</span>
                      <div className="h-1.5 w-24 overflow-hidden rounded-full bg-off">
                        <div
                          className={`h-full ${h.quality >= 70 ? "bg-positive" : "bg-critical"}`}
                          style={{ width: `${Math.min(100, h.quality)}%` }}
                        />
                      </div>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}
