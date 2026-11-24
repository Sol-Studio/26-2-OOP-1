/** 생육 단계 타임라인: 단계별 구간, 현재 생장도, 수확 예상 */
export default function GrowthTimeline({ section: s }) {
  const ps = s.plant;
  if (!ps) {
    return (
      <div className="mt-4">
        <p className="text-sm">
          <span className="font-bold">생육 단계</span>
          <span className="ml-3 text-muted">빈 구역 · 작물을 고르고 '심기'를 누르세요</span>
        </p>
        <div className="mt-2 h-3.5 rounded bg-off" />
      </div>
    );
  }

  const stages = s.stages;
  const fill = !ps.alive ? "bg-dead" : ps.ready ? "bg-ready" : "bg-brand";
  let info, infoColor;
  if (!ps.alive) [info, infoColor] = ["고사 · '정리'로 비우세요", "text-dead"];
  else if (ps.ready) [info, infoColor] = ["수확 가능 · 늦으면 상합니다", "text-ready"];
  else [info, infoColor] = [ps.daysToHarvest == null ? "수확까지 계산 중" : `수확까지 약 ${ps.daysToHarvest.toFixed(1)}일`, "text-ink"];

  return (
    <div className="mt-4">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 text-sm">
        <p>
          <span className="font-bold">생육 단계</span>
          <span className={`ml-3 ${infoColor}`}>
            {ps.stage} {Math.round(ps.growth)}% · {info}
          </span>
        </p>
        <p className="tabular text-xs text-muted">
          파종 후 {ps.ageDays.toFixed(1)}일 · 평균 건강 {Math.round(ps.avgHealth)} · 예상 수확량 {ps.expectedKg.toFixed(1)}kg
        </p>
      </div>

      <div className="relative mt-3">
        <div
          className="absolute -top-2 size-0 -translate-x-1/2 border-x-[5px] border-t-[7px] border-x-transparent border-t-ink transition-[left] duration-300"
          style={{ left: `${ps.growth}%` }}
          aria-hidden
        />
        <div className="relative h-3.5 overflow-hidden rounded bg-off">
          <div className={`h-full ${fill} transition-[width] duration-300`} style={{ width: `${ps.growth}%` }} />
          {stages.slice(1, -1).map(([name, start]) => (
            <div key={name} className="absolute inset-y-0 w-0.5 bg-card" style={{ left: `${start}%` }} />
          ))}
        </div>
        <div className="relative mt-1 h-4 text-[11px]">
          {stages.slice(0, -1).map(([name, start], k) => {
            const end = stages[k + 1][1];
            const current = name === ps.stage;
            return (
              <span
                key={name}
                className={`absolute -translate-x-1/2 whitespace-nowrap ${current ? "font-bold text-ink" : "text-muted"}`}
                style={{ left: `${(start + end) / 2}%` }}
              >
                {name}
              </span>
            );
          })}
        </div>
      </div>
    </div>
  );
}
