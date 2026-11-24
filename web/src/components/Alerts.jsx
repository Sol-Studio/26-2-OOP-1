import { useEffect, useRef, useState } from "react";
import { useFarm } from "../lib/farm.jsx";

const LIST_MAX = 40;

/** 새 경고(병충해·고사·방제 실패 등)를 화면 구석에 잠깐 띄운다. 누르면 그 구역을 고른다. */
export function AlertToasts() {
  const { alerts, dismissAlert, select, zoneIndex } = useFarm();
  if (!alerts.length) return null;
  return (
    <div className="fixed bottom-4 right-4 z-40 flex w-[min(92vw,360px)] flex-col gap-2" role="status" aria-live="polite">
      {alerts.map((e) => {
        const i = e.zone ? zoneIndex(e.zone) : -1;
        return (
          <div key={e.seq} className="flex items-start gap-2 rounded-lg border-l-4 border-critical bg-card p-3 text-sm shadow-lg ring-1 ring-line">
            <span aria-hidden className="mt-0.5 text-critical">⚠</span>
            <button
              className="flex-1 text-left"
              onClick={() => {
                if (i >= 0) select(i);
                dismissAlert(e.seq);
              }}
            >
              {e.text}
              {i >= 0 && <span className="mt-1 block text-xs font-bold text-brand-pressed">{e.zone} 보기 →</span>}
            </button>
            <button onClick={() => dismissAlert(e.seq)} className="px-1 text-muted hover:text-ink" aria-label="알림 닫기">
              ✕
            </button>
          </div>
        );
      })}
    </div>
  );
}

/** 상단 바의 알림 종: 안 읽은 경고 개수, 누르면 최근 경고 목록 */
export function AlertBell() {
  const { logs, seenSeq, markSeen, select, zoneIndex } = useFarm();
  const [open, setOpen] = useState(false);
  const box = useRef(null);
  const warns = logs.filter((e) => e.warn);
  const unread = warns.filter((e) => e.seq > seenSeq).length;

  useEffect(() => {
    if (!open) return;
    const close = (e) => !box.current?.contains(e.target) && setOpen(false);
    const esc = (e) => e.key === "Escape" && setOpen(false);
    document.addEventListener("pointerdown", close);
    document.addEventListener("keydown", esc);
    return () => {
      document.removeEventListener("pointerdown", close);
      document.removeEventListener("keydown", esc);
    };
  }, [open]);

  return (
    <div ref={box} className="relative">
      <button
        onClick={() => {
          setOpen(!open);
          markSeen();
        }}
        aria-expanded={open}
        aria-label={`경고 알림 ${unread}건 안 읽음`}
        className="relative rounded-md px-2.5 py-1.5 text-muted ring-1 ring-line hover:bg-pressed hover:text-ink"
      >
        <span aria-hidden>🔔</span>
        {unread > 0 && (
          <span className="tabular absolute -right-1.5 -top-1.5 min-w-[18px] rounded-full bg-critical px-1 text-center text-[10px] font-bold leading-[18px] text-white">
            {Math.min(unread, 99)}
          </span>
        )}
      </button>
      {open && (
        <div className="absolute right-0 top-11 z-50 w-[min(92vw,400px)] overflow-hidden rounded-xl bg-card shadow-xl ring-1 ring-line">
          <p className="border-b border-line px-4 py-2.5 text-sm font-bold">경고 {warns.length}건 · 최근 것부터</p>
          <ul className="max-h-96 overflow-y-auto">
            {warns.length === 0 && <li className="px-4 py-8 text-center text-sm text-muted">아직 경고가 없습니다.</li>}
            {warns
              .slice(-LIST_MAX)
              .reverse()
              .map((e) => {
                const i = e.zone ? zoneIndex(e.zone) : -1;
                return (
                  <li key={e.seq}>
                    <button
                      disabled={i < 0}
                      onClick={() => {
                        select(i);
                        setOpen(false);
                      }}
                      className="w-full border-b border-line/60 px-4 py-2.5 text-left text-sm hover:bg-pressed disabled:cursor-default disabled:hover:bg-transparent"
                    >
                      {e.text}
                    </button>
                  </li>
                );
              })}
          </ul>
        </div>
      )}
    </div>
  );
}
