import { useEffect, useMemo, useRef } from "react";
import { COLORS, Chart, nightShade } from "../lib/chart.js";
import { useFarm } from "../lib/farm.jsx";
import { clock, metricValue } from "../lib/format.js";

/** 최근 24시간 그래프 6개 (chart.js): 적정 범위 띠, 밤 음영, 시간 눈금, 마우스를 올리면 그 시각의 값 */
export default function ChartGrid({ section: s }) {
  const { meta, history, nights, state } = useFarm();
  const hist = history?.[s.index];
  // 그래프 칸마다의 시각: 마지막 값이 지금이고 10분 간격
  const times = useMemo(
    () => (hist ? hist.map((_, i) => clock((((state.hours - (hist.length - 1 - i) / 6) % 24) + 24) % 24)) : []),
    [hist, state.hours],
  );
  if (!meta || !hist) return null;

  return (
    <div className="mt-4">
      <div className="grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-3">
        {meta.metrics.map((m, k) => (
          <MetricChart key={m.key} metric={m} band={s.bands[k]} values={hist.map((h) => h[k])} nights={nights} times={times} />
        ))}
      </div>
      <p className="mt-2 text-xs text-muted">
        최근 24시간 · <span className="inline-block size-2 rounded-sm bg-band ring-1 ring-positive/30" /> 적정 범위 ·{" "}
        <span className="inline-block size-2 rounded-sm bg-night ring-1 ring-line" /> 밤 · 그래프에 마우스를 올리면 그 시각의 값
      </p>
    </div>
  );
}

function MetricChart({ metric, band, values, nights, times }) {
  const canvas = useRef(null);
  const chart = useRef(null);
  const [lo, hi] = metric.range;
  const cur = values.at(-1) ?? 0;
  const ok = band[0] <= cur && cur <= band[1];

  useEffect(() => {
    chart.current = new Chart(canvas.current, {
      type: "line",
      data: { labels: [], datasets: [] },
      plugins: [nightShade],
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        layout: { padding: { top: 4, right: 6 } },
        scales: {
          x: { grid: { display: false }, ticks: { maxRotation: 0, maxTicksLimit: 4, font: { size: 10 } } },
          y: {
            min: lo,
            max: hi,
            grid: { color: COLORS.grid },
            border: { display: false },
            ticks: { maxTicksLimit: 3, font: { size: 10 }, callback: (v) => (hi >= 10000 ? `${v / 1000}k` : v) },
          },
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            filter: (item) => item.datasetIndex === 2,
            displayColors: false,
            callbacks: { label: (ctx) => `${metric.title} ${metricValue(ctx.parsed.y, hi)} ${metric.unit}` },
          },
        },
      },
    });
    return () => chart.current.destroy();
  }, [lo, hi, metric.title, metric.unit]);

  useEffect(() => {
    const ch = chart.current;
    const last = values.length - 1;
    const flat = (v) => values.map(() => Math.min(v, hi));
    ch.data.labels = times;
    ch.data.datasets = [
      // order가 작을수록 위에 그려진다: 값 선(0)이 적정 범위 띠(1) 위로
      { data: flat(band[1]), borderWidth: 0, pointRadius: 0, fill: "+1", backgroundColor: COLORS.band, order: 1 }, // 적정 범위 띠
      { data: flat(band[0]), borderWidth: 0, pointRadius: 0, order: 1 },
      {
        order: 0,
        data: values,
        borderColor: COLORS.brand,
        borderWidth: 2,
        tension: 0.25,
        pointRadius: (c) => (c.dataIndex === last ? 3.5 : 0),
        pointHoverRadius: 4,
        pointBackgroundColor: (c) => {
          const v = values[c.dataIndex];
          return v < band[0] || v > band[1] ? COLORS.critical : COLORS.brand;
        },
        pointBorderWidth: 0,
      },
    ];
    ch.options.plugins.nightShade = { nights };
    ch.update("none");
  }, [values, band, nights, times, hi]);

  return (
    <figure>
      <figcaption className="mb-1 flex items-baseline justify-between gap-2 text-xs">
        <span className="font-bold text-ink">{metric.title}</span>
        <span className={`tabular font-mono font-bold ${ok ? "text-ink" : "text-critical"}`}>
          {!ok && <span className="mr-1 font-sans text-[10px]">범위 밖</span>}
          {metricValue(cur, hi)} <span className="font-sans font-normal text-muted">{metric.unit}</span>
        </span>
      </figcaption>
      <div className="relative h-24 rounded-md bg-card ring-1 ring-line">
        <canvas ref={canvas} role="img" aria-label={`${metric.title} 최근 24시간 그래프, 지금 ${metricValue(cur, hi)} ${metric.unit}`} />
      </div>
    </figure>
  );
}
