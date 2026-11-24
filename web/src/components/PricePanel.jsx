import { useMemo, useState } from "react";
import { useFarm } from "../lib/farm.jsx";
import { num } from "../lib/format.js";
import CandleChart, { DOWN, UP } from "./CandleChart.jsx";
import { Card } from "./ui.jsx";

// 기간마다 캔들 하나의 길이 (시간)
const PERIODS = [
  { days: 1, hours: 1, name: "1일 · 1시간봉" },
  { days: 7, hours: 6, name: "7일 · 6시간봉" },
  { days: 30, hours: 24, name: "30일 · 일봉" },
];
const STEP_H = 1 / 6; // 시세는 10분마다 하나씩 기록된다

/** 10분 단위 시세를 period시간짜리 캔들(시가·고가·저가·종가)로 묶는다.
 *  values의 마지막 값이 지금(nowHours) 시세다. 캔들 경계는 시뮬레이션 시각에 맞춰서 시간이 흘러도 흔들리지 않는다. */
function toCandles(values, nowHours, period, days) {
  const from = nowHours - days * 24;
  const out = [];
  values.forEach((v, i) => {
    const t = nowHours - (values.length - 1 - i) * STEP_H;
    if (t < from - 1e-6) return;
    const b = Math.floor(t / period.hours + 1e-6);
    const last = out.at(-1);
    if (last?.b === b) {
      last.h = Math.max(last.h, v);
      last.l = Math.min(last.l, v);
      last.c = v;
    } else {
      out.push({ b, o: v, h: v, l: v, c: v, label: candleLabel(b * period.hours, period.hours) });
    }
  });
  return out;
}

function candleLabel(start, period) {
  const day = Math.floor(start / 24) + 1;
  return period >= 24 ? `Day ${day}` : `D${day} ${String(start % 24).padStart(2, "0")}시`;
}

/** 작물 시세: 고른 작물의 캔들 차트와 작물별 현재 시세 */
export default function PricePanel() {
  const { state, meta, priceHistory } = useFarm();
  const [period, setPeriod] = useState(PERIODS[1]);
  const [crop, setCrop] = useState("상추");
  const values = priceHistory?.[crop];

  const candles = useMemo(
    () => (values ? toCandles(values.slice(-(period.days * 144 + 1)), state.hours, period, period.days) : []),
    [values, state.hours, period],
  );
  if (!meta || !priceHistory) return null;

  const p = state.prices[crop];
  const hi = candles.length ? Math.max(...candles.map((c) => c.h)) : p.now;
  const lo = candles.length ? Math.min(...candles.map((c) => c.l)) : p.now;

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_300px]">
      <Card>
        <header className="mb-4 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="text-sm font-bold text-ink">{crop} 시세</h2>
            <p className="tabular mt-1 flex items-baseline gap-2">
              <span className="text-2xl font-bold">{num(p.now)}원</span>
              <span className="text-sm font-bold" style={{ color: p.change >= 0 ? UP : DOWN }}>
                {p.change >= 0 ? "▲" : "▼"} {Math.abs(p.change).toFixed(1)}%
              </span>
              <span className="text-xs text-muted">
                기간 고가 {num(hi)} · 저가 {num(lo)} · 기준 {num(p.base)}
              </span>
            </p>
          </div>
          <div className="flex rounded-lg bg-bg p-1" role="radiogroup" aria-label="기간">
            {PERIODS.map((pd) => (
              <button
                key={pd.days}
                role="radio"
                aria-checked={period === pd}
                onClick={() => setPeriod(pd)}
                className={`rounded-md px-3 py-1 text-xs font-medium ${period === pd ? "bg-card text-ink shadow-sm" : "text-muted"}`}
              >
                {pd.name}
              </button>
            ))}
          </div>
        </header>
        <CandleChart candles={candles} base={p.base} label={`${crop} 최근 ${period.days}일 시세 캔들 차트`} />
        <p className="mt-3 text-xs text-muted">
          빨간 캔들은 그 구간에 올랐고(종가 ≥ 시가) 파란 캔들은 내렸다는 뜻입니다. 점선은 기준가입니다. 많이 수확해 팔면 그 작물
          시세가 내려가고, 시간이 지나면 기준가로 돌아옵니다.
        </p>
      </Card>

      <Card title="현재 시세" aside="하루 전 대비">
        <ul className="-mx-2">
          {meta.crops.map((name) => {
            const q = state.prices[name];
            if (!q) return null;
            const up = q.change >= 0;
            return (
              <li key={name}>
                <button
                  onClick={() => setCrop(name)}
                  aria-pressed={crop === name}
                  className={`flex w-full items-center gap-3 rounded-lg px-2 py-2.5 text-left ${
                    crop === name ? "bg-brand-weak ring-1 ring-brand" : "hover:bg-pressed"
                  }`}
                >
                  <div className="flex-1">
                    <p className="text-sm font-bold">{name}</p>
                    <p className="tabular font-mono text-sm">{num(q.now)}원</p>
                  </div>
                  <div className="text-right">
                    <p className="tabular text-sm font-bold" style={{ color: up ? UP : DOWN }}>
                      {up ? "▲" : "▼"} {Math.abs(q.change).toFixed(1)}%
                    </p>
                    <p className="tabular text-xs text-muted">기준 {num(q.base)}</p>
                  </div>
                </button>
              </li>
            );
          })}
        </ul>
      </Card>
    </div>
  );
}
