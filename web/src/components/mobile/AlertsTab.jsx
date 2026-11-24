import { useFarm } from "../../lib/farm.jsx";
import { MobileHeader } from "./MobileApp.jsx";

const SHOW = 100;

/** 알림: 경고 로그를 최근 것부터 */
export default function AlertsTab() {
  const { logs } = useFarm();
  const warns = logs.filter((e) => e.warn);

  return (
    <>
      <MobileHeader title="알림" sub={`경고 ${warns.length}건 · 최근 것부터`} />
      {warns.length === 0 ? (
        <p className="py-16 text-center text-sm text-muted">아직 알림이 없습니다.</p>
      ) : (
        <ul className="space-y-2">
          {warns
            .slice(-SHOW)
            .reverse()
            .map((e) => (
              <li key={e.seq} className="rounded-xl border-l-4 border-critical bg-card px-3 py-2.5 text-sm ring-1 ring-line">
                {e.text}
              </li>
            ))}
        </ul>
      )}
    </>
  );
}
