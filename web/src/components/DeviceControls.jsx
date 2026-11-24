import { useFarm } from "../lib/farm.jsx";
import { DEVICES, MODE_NAMES, deviceLabel, deviceOn } from "../lib/format.js";

/** 장치 8개의 상태와 운전 방식. 자동이면 장치가 스스로 판단하고, 켜기·끄기를 누르면 관리자가 정한 대로 수동 운전한다.
 *  급수·비료는 켜 둘 수 없어서 자동/끄기와 '지금 주기'만 있다. 장치마다 지금 상태가 된 이유를 보여 준다. */
export default function DeviceControls({ section: s, className = "grid-cols-2 2xl:grid-cols-4" }) {
  const { meta, actions } = useFarm();
  const d = s.devices;
  const growing = !!s.plant?.alive;
  const modesOf = Object.fromEntries((meta?.devices ?? []).map((x) => [x.key, x.modes]));

  return (
    <ul data-tour="devices" className={`grid gap-2 ${className}`} aria-label="장치 제어">
      {DEVICES.map(([key, name]) => {
        const on = deviceOn(key, d);
        const mode = d.modes[key];
        const manual = mode !== "auto";
        const reason = !growing ? "작물이 없어 멈춤" : d.reasons[key] || (on ? "자동 운전 중" : "적정 범위 안 · 대기");
        return (
          <li key={key} className={`rounded-lg p-2.5 ${manual ? "bg-brand-weak ring-1 ring-brand" : "bg-pressed ring-1 ring-line"}`}>
            <div className="flex items-center justify-between gap-1">
              <span className="truncate text-sm font-bold">{deviceLabel(key, name, d)}</span>
              <span
                className={`shrink-0 rounded px-1.5 py-0.5 text-[10px] font-bold ${on ? "bg-brand text-white" : "bg-off text-muted"}`}
              >
                {on ? "● 켜짐" : "○ 꺼짐"}
              </span>
            </div>
            <p className="mt-1 truncate text-[11px] text-muted" title={reason}>
              {manual && <b className="text-brand-pressed">수동 · </b>}
              {reason}
            </p>
            <div className="mt-2 flex gap-1">
              <div className="flex flex-1 rounded-md bg-card p-0.5 ring-1 ring-line" role="radiogroup" aria-label={`${name} 운전 방식`}>
                {(modesOf[key] ?? ["auto"]).map((m) => (
                  <button
                    key={m}
                    role="radio"
                    aria-checked={mode === m}
                    onClick={() => mode !== m && actions.setDeviceMode(s.index, key, m)}
                    className={`flex-1 rounded px-1 py-1 text-[11px] font-medium ${
                      mode === m ? (m === "auto" ? "bg-ink text-white" : "bg-brand text-white") : "text-muted hover:text-ink"
                    }`}
                  >
                    {MODE_NAMES[m]}
                  </button>
                ))}
              </div>
              {(key === "irrigation" || key === "fertilizer") && (
                <button
                  onClick={() => (growing ? actions.dose(s.index, key) : actions.notice("작물이 없어서 줄 수 없습니다."))}
                  aria-disabled={!growing}
                  className={`rounded-md bg-card px-2 text-[11px] font-bold ring-1 ring-line hover:bg-off ${growing ? "" : "opacity-50"}`}
                >
                  지금 주기
                </button>
              )}
            </div>
          </li>
        );
      })}
    </ul>
  );
}
