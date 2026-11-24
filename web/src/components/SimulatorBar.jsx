import { useEffect, useState } from "react";
import { useFarm } from "../lib/farm.jsx";
import { SPEEDS, speedText } from "../lib/format.js";

/** 시뮬레이터: 농장 관리 화면이 아니라 시험용 조작 도구라서 어두운 띠로 따로 둔다.
 *  진행 제어, 속도, 계절 건너뛰기, 바깥 날씨(한파·폭염), 병충해 일부러 발생시키기 */
export default function SimulatorBar() {
  const { state, meta, actions, selected } = useFarm();
  const [pestZone, setPestZone] = useState(selected);

  useEffect(() => setPestZone(selected), [selected]);

  if (!meta) return null;

  return (
    <section aria-label="시뮬레이터" className="bg-dark text-dark-text">
      <div className="mx-auto flex max-w-[1600px] flex-wrap items-center gap-x-6 gap-y-2 px-4 py-2 text-sm lg:px-6">
        <span className="text-xs font-bold text-subtle">시뮬레이터</span>

        <div className="flex gap-1.5">
          <DarkButton onClick={() => actions.setSim({ running: !state.running })} strong>
            {state.running ? "⏸ 정지" : "▶ 시작"}
          </DarkButton>
          <DarkButton onClick={actions.step}>10분 진행</DarkButton>
          <DarkButton onClick={actions.reset}>초기화</DarkButton>
        </div>

        <Segment
          label="속도"
          hint={speedText(state.speed)}
          options={SPEEDS.map((s) => ({ key: s.ms, text: s.label }))}
          value={state.speed}
          onPick={(ms) => actions.setSim({ speed: ms })}
        />

        <Segment
          label="계절"
          hint={state.weather.season ? `${state.weather.season} ${state.weather.seasonDay}일째` : ""}
          options={meta.seasons.map((name) => ({ key: name, text: name }))}
          value={state.weather.season}
          onPick={(season) => actions.setSim({ season })}
          title="누르면 그 계절 한가운데로 달력을 옮깁니다 (1년 = 120일)"
        />

        <Segment
          label="바깥 날씨"
          options={meta.weather.map(({ label, delta }) => ({ key: delta, text: delta ? `${label} ${delta > 0 ? "+" : ""}${delta}°C` : label }))}
          value={state.weatherDelta}
          onPick={(weather) => actions.setSim({ weather })}
        />

        <div className="flex items-center gap-2">
          <span className="text-subtle">병충해</span>
          <select
            value={pestZone}
            onChange={(e) => setPestZone(+e.target.value)}
            className="rounded-md border border-dark-2 bg-dark-2 px-2 py-1 text-xs text-white"
            aria-label="병충해를 일으킬 구역"
          >
            {meta.zones.map((z, i) => (
              <option key={z} value={i}>{z}</option>
            ))}
          </select>
          <DarkButton onClick={() => actions.pests(pestZone)}>발생시키기</DarkButton>
        </div>
      </div>
    </section>
  );
}

function Segment({ label, hint, options, value, onPick, title }) {
  return (
    <div className="flex items-center gap-2" role="radiogroup" aria-label={label} title={title}>
      <span className="text-subtle">{label}</span>
      <div className="flex rounded-md bg-dark-2 p-0.5">
        {options.map((o) => (
          <button
            key={o.key}
            role="radio"
            aria-checked={value === o.key}
            onClick={() => onPick(o.key)}
            className={`rounded px-2.5 py-1 text-xs font-medium ${value === o.key ? "bg-card text-ink" : "text-dark-text hover:text-white"}`}
          >
            {o.text}
          </button>
        ))}
      </div>
      {hint && <span className="tabular text-xs text-subtle">{hint}</span>}
    </div>
  );
}

function DarkButton({ children, strong, ...props }) {
  return (
    <button
      {...props}
      className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
        strong ? "bg-brand text-white hover:bg-brand-pressed" : "bg-dark-2 text-white hover:bg-muted"
      }`}
    >
      {children}
    </button>
  );
}
