import { useEffect, useRef } from "react";
import { Chart } from "../lib/chart.js";
import { num } from "../lib/format.js";

export const UP = "#fa342c"; // 상승 (국내 관례대로 빨강)
export const DOWN = "#217cf9"; // 하락

/** 캔들 차트. chart.js 막대 차트의 '떠 있는 막대'([아래, 위])로 그린다:
 *  가는 막대 = 고가~저가 꼬리, 굵은 막대 = 시가~종가 몸통. 점선은 기준가. */
export default function CandleChart({ candles, base, label }) {
  const canvas = useRef(null);
  const chart = useRef(null);
  const data = useRef(candles);
  data.current = candles;

  useEffect(() => {
    chart.current = new Chart(canvas.current, {
      type: "bar",
      data: { labels: [], datasets: [] },
      options: {
        animation: false,
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        scales: {
          x: { grid: { display: false }, ticks: { maxRotation: 0, autoSkipPadding: 16 } },
          y: {
            beginAtZero: false, // 막대 차트는 기본이 0부터라서 캔들이 위로 눌린다
            grace: "8%",
            grid: { color: "#eeeff1" },
            border: { display: false },
            ticks: { callback: (v) => num(v) },
            title: { display: true, text: "원/kg", color: "#868b94" },
          },
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            filter: (item) => item.datasetIndex === 1,
            displayColors: false,
            callbacks: {
              label: (ctx) => {
                const c = data.current[ctx.dataIndex];
                if (!c) return "";
                const change = ((c.c / c.o - 1) * 100).toFixed(1);
                return [`시가 ${num(c.o)}원`, `고가 ${num(c.h)}원`, `저가 ${num(c.l)}원`, `종가 ${num(c.c)}원 (${change}%)`];
              },
            },
          },
        },
      },
    });
    return () => chart.current.destroy();
  }, []);

  useEffect(() => {
    const ch = chart.current;
    const colors = candles.map((c) => (c.c >= c.o ? UP : DOWN));
    ch.data.labels = candles.map((c) => c.label);
    ch.data.datasets = [
      {
        label: "고가·저가",
        data: candles.map((c) => [c.l, c.h]),
        backgroundColor: colors,
        grouped: false,
        barPercentage: 0.12,
        categoryPercentage: 1,
        order: 2,
      },
      {
        label: "시가·종가",
        data: candles.map((c) => [c.o, c.c]),
        backgroundColor: colors,
        grouped: false,
        barPercentage: 0.7,
        categoryPercentage: 1,
        minBarLength: 2, // 시가와 종가가 같아도 가로줄로 보이게
        order: 1,
      },
      {
        type: "line",
        label: "기준가",
        data: candles.map(() => base),
        borderColor: "#868b94",
        borderWidth: 1,
        borderDash: [4, 4],
        pointRadius: 0,
        order: 0,
      },
    ];
    ch.update("none");
  }, [candles, base]);

  return (
    <div className="relative h-[400px]">
      <canvas ref={canvas} role="img" aria-label={label} />
    </div>
  );
}
