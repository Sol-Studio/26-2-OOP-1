import { useFarm } from "../lib/farm.jsx";
import { clock, num } from "../lib/format.js";
import { AlertBell } from "./Alerts.jsx";

const VIEWS = [
  ["panel", "관리 패널"],
  ["prices", "작물 시세"],
  ["crops", "작물 설정"],
  ["mobile", "모바일 앱"],
];

/** 맨 위: 날짜·계절·시각, 바깥 날씨, 하루 진행 막대, 화면 전환, 경고 알림, 로그아웃 */
export default function TopBar({ view, setView, onHelp }) {
  const { state, user, logout, connected } = useFarm();
  const { day, hour, weather: w } = state;

  return (
    <header className="sticky top-0 z-30 border-b border-line bg-card/95 backdrop-blur">
      <div className="mx-auto flex max-w-[1600px] flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3 lg:px-6">
        <div className="flex items-center gap-2.5">
          <img src="/favicon.svg" alt="" className="size-7" />
          <span className="font-bold text-ink">에버그로우</span>
        </div>

        <div className="flex min-w-0 flex-1 items-center gap-4">
          <div className="tabular shrink-0 text-lg font-bold text-ink">
            Day {day} <span className="ml-1">{clock(hour)}</span>
            {w.season && <span className="ml-2 rounded-md bg-bg px-2 py-0.5 align-middle text-xs font-medium text-muted">{w.season} {w.seasonDay}일째</span>}
          </div>
          <div className="hidden min-w-0 flex-1 flex-col gap-1.5 lg:flex">
            <p className="tabular truncate text-sm text-muted">
              바깥 {w.temperature.toFixed(1)}°C · 습도 {Math.round(w.humidity)}% · 햇빛 {num(w.sunlight)}lux · {w.sky}
            </p>
            <DayBar hour={hour} />
          </div>
        </div>

        <nav data-tour="tabs" className="flex rounded-lg bg-bg p-1" aria-label="화면">
          {VIEWS.map(([key, name]) => (
            <button
              key={key}
              onClick={() => setView(key)}
              aria-current={view === key ? "page" : undefined}
              className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                view === key ? "bg-card text-ink shadow-sm" : "text-muted hover:text-ink"
              }`}
            >
              {name}
            </button>
          ))}
        </nav>

        <div className="flex items-center gap-3 text-sm">
          <button onClick={onHelp} className="rounded-md px-2.5 py-1.5 text-muted ring-1 ring-line hover:bg-pressed hover:text-ink" title="새싹봇 사용 안내 다시 보기">
            도움말
          </button>
          <AlertBell />
          <span className="flex items-center gap-1.5 text-muted" title={connected ? "서버와 연결됨" : "다시 연결하는 중"}>
            <span className={`size-2 rounded-full ${connected ? "bg-positive" : "bg-critical"}`} />
            {user}
          </span>
          <button onClick={logout} className="rounded-md px-2.5 py-1.5 text-muted ring-1 ring-line hover:bg-pressed hover:text-ink">
            로그아웃
          </button>
        </div>
      </div>
    </header>
  );
}

/** 하루 진행 막대: 6~18시는 낮 */
function DayBar({ hour }) {
  return (
    <div className="relative h-1.5 max-w-md rounded-full bg-night" aria-hidden>
      <div className="absolute inset-y-0 rounded-full bg-day" style={{ left: "25%", width: "50%" }} />
      <div
        className="absolute top-1/2 size-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-card bg-ink"
        style={{ left: `${(hour / 24) * 100}%` }}
      />
    </div>
  );
}
