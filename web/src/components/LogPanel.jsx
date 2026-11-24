import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { useFarm } from "../lib/farm.jsx";

const MAX_LINES = 500;

/** 로그: 구역별로 걸러 보기 (구역 표시가 없는 날씨 등 공통 로그는 항상 보인다). 주황 줄은 경고 */
export default function LogPanel() {
  const { logs, meta, selected } = useFarm();
  const [filter, setFilter] = useState("전체");
  const box = useRef(null);
  const stick = useRef(true);

  // 구역 로그를 보는 중이면 선택한 구역으로 따라간다
  useEffect(() => {
    if (meta) setFilter((f) => (f === "전체" ? f : meta.zones[selected]));
  }, [selected, meta]);

  const lines = useMemo(
    () => logs.filter((e) => filter === "전체" || e.zone == null || e.zone === filter).slice(-MAX_LINES),
    [logs, filter],
  );

  // 맨 아래를 보고 있을 때만 새 줄을 따라 내려간다
  useLayoutEffect(() => {
    const el = box.current;
    if (el && stick.current) el.scrollTop = el.scrollHeight;
  }, [lines]);

  return (
    <section className="overflow-hidden rounded-xl bg-dark ring-1 ring-line">
      <header className="flex flex-wrap items-center gap-1 border-b border-dark-2 px-3 py-2">
        <h2 className="mr-2 text-sm font-bold text-white">로그</h2>
        {["전체", ...(meta?.zones ?? [])].map((name) => (
          <button
            key={name}
            onClick={() => setFilter(name)}
            aria-pressed={filter === name}
            className={`rounded px-2 py-0.5 text-xs ${filter === name ? "bg-card font-bold text-ink" : "text-dark-text hover:bg-dark-2"}`}
          >
            {name}
          </button>
        ))}
      </header>
      <div
        ref={box}
        onScroll={(e) => {
          const el = e.currentTarget;
          stick.current = el.scrollHeight - el.scrollTop - el.clientHeight < 24;
        }}
        className="h-56 overflow-y-auto px-3 py-2 font-mono text-xs leading-5"
        role="log"
        aria-live="off"
      >
        {lines.map((e) => (
          <p key={e.seq} className={e.warn ? "text-dark-warn" : "text-dark-text"}>
            {e.text}
          </p>
        ))}
      </div>
    </section>
  );
}
