import { useEffect, useRef } from "react";
import { COLORS, Chart } from "../lib/chart.js";
import { num } from "../lib/format.js";

/** 일별 정산: 매출(위로 막대), 비용(아래로 막대), 순이익(선). 끝난 재배(수확·갈아엎기·고사) 기준이고 마지막 칸은 오늘(진행 중). */
export default function LedgerChart({ ledger }) {
  const canvas = useRef(null);
  const chart = useRef(null);

  useEffect(() => {
    chart.current = new Chart(canvas.current, {
      type: "bar",
      data: { labels: [], datasets: [] },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        scales: {
          x: { stacked: true, grid: { display: false }, ticks: { maxRotation: 0, autoSkipPadding: 12, font: { size: 10 } } },
          y: {
            stacked: true,
            suggestedMin: -10000, // 아직 정산이 없어도 눈금이 0 하나로 뭉개지지 않게
            suggestedMax: 10000,
            grid: { color: COLORS.grid },
            border: { display: false },
            ticks: { maxTicksLimit: 5, font: { size: 10 }, callback: (v) => (Math.abs(v) >= 10000 ? `${v / 10000}만` : num(v)) },
          },
        },
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: (ctx) => `${ctx.dataset.label} ${num(Math.abs(ctx.parsed.y))}원` } },
        },
      },
    });
    return () => chart.current.destroy();
  }, []);

  useEffect(() => {
    const ch = chart.current;
    ch.data.labels = ledger.map((d, i) => (i === ledger.length - 1 ? `Day ${d.day} (오늘)` : `Day ${d.day}`));
    ch.data.datasets = [
      { type: "line", label: "순이익", data: ledger.map((d) => d.profit), borderColor: "#1a1c20", borderWidth: 2, pointRadius: 2, order: 0, stack: "line" },
      { label: "매출", data: ledger.map((d) => d.revenue), backgroundColor: COLORS.positive, order: 1, stack: "money" },
      { label: "비용", data: ledger.map((d) => -d.cost), backgroundColor: COLORS.critical, order: 1, stack: "money" },
    ];
    ch.update("none");
  }, [ledger]);

  return (
    <figure className="mb-4">
      <figcaption className="mb-1 flex flex-wrap items-center gap-x-3 text-xs text-muted">
        <span className="font-bold text-ink">일별 정산</span>
        <span>
          <i className="mr-1 inline-block size-2 rounded-sm bg-positive" />매출
        </span>
        <span>
          <i className="mr-1 inline-block size-2 rounded-sm bg-critical" />비용(아래)
        </span>
        <span>
          <i className="mr-1 inline-block h-0.5 w-3 bg-ink align-middle" />순이익
        </span>
        <span className="ml-auto">끝난 재배 기준</span>
      </figcaption>
      <div className="relative h-40">
        <canvas ref={canvas} role="img" aria-label="최근 날짜별 매출·비용·순이익 그래프" />
      </div>
    </figure>
  );
}
