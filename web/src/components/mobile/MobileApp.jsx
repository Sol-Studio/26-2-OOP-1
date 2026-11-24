import { useState } from "react";
import { useFarm } from "../../lib/farm.jsx";
import { clock } from "../../lib/format.js";
import HomeTab from "./HomeTab.jsx";
import CctvTab from "./CctvTab.jsx";
import ZoneTab from "./ZoneTab.jsx";
import AlertsTab from "./AlertsTab.jsx";

const TABS = [
  ["home", "홈", HomeTab],
  ["cctv", "CCTV", CctvTab],
  ["zone", "구역", ZoneTab],
  ["alerts", "알림", AlertsTab],
];

/** 농장주가 휴대폰으로 보는 앱. 홈 / CCTV / 구역 상세 / 알림 네 탭을 오간다. */
export default function MobileApp() {
  const { state, logs, logout } = useFarm();
  const [tab, setTab] = useState("home");
  const warns = logs.reduce((n, e) => n + (e.warn ? 1 : 0), 0);
  const Tab = TABS.find(([key]) => key === tab)[2];

  return (
    <div className="flex h-full flex-col bg-bg">
      <div className="flex shrink-0 items-center justify-between bg-dark px-4 py-1.5 text-xs">
        <span className="tabular font-bold text-white">{clock(state.hour)}</span>
        <button onClick={logout} className="text-dark-text">EverGrow · 로그아웃</button>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-4 pb-4 pt-4">
        <Tab go={setTab} />
      </div>

      <nav className="grid shrink-0 grid-cols-4 border-t border-line bg-card" aria-label="탭">
        {TABS.map(([key, name]) => {
          const on = key === tab;
          return (
            <button
              key={key}
              onClick={() => setTab(key)}
              aria-current={on ? "page" : undefined}
              className={`relative py-3.5 text-sm ${on ? "font-bold text-ink" : "text-subtle"}`}
            >
              {on && <span className="absolute left-1/2 top-1 h-[3px] w-9 -translate-x-1/2 rounded-full bg-brand" />}
              {name}
              {key === "alerts" && warns > 0 && (
                <span className="tabular absolute right-[18%] top-2 min-w-[18px] rounded-full bg-critical px-1 text-[10px] font-bold leading-[18px] text-white">
                  {Math.min(warns, 99)}
                </span>
              )}
            </button>
          );
        })}
      </nav>
    </div>
  );
}

export function MobileHeader({ title, sub, onBack }) {
  return (
    <header className="mb-4">
      {onBack ? (
        <button onClick={onBack} className="text-xl font-bold text-ink">
          ‹ {title}
        </button>
      ) : (
        <h1 className="text-xl font-bold text-ink">{title}</h1>
      )}
      {sub && <p className="mt-1 text-sm text-muted">{sub}</p>}
    </header>
  );
}
