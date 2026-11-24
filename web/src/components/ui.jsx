import { useFarm } from "../lib/farm.jsx";

/** 여러 화면이 같이 쓰는 작은 조각 */

export function Card({ title, aside, className = "", children, ...rest }) {
  return (
    <section {...rest} className={`rounded-xl bg-card p-4 ring-1 ring-line ${className}`}>
      {(title || aside) && (
        <header className="mb-3 flex items-baseline justify-between gap-3">
          {title && <h2 className="text-sm font-bold text-ink">{title}</h2>}
          {aside && <div className="tabular truncate text-xs text-muted">{aside}</div>}
        </header>
      )}
      {children}
    </section>
  );
}

export function Bar({ value, color, className = "h-1.5" }) {
  return (
    <div className={`overflow-hidden rounded-full bg-off ${className}`}>
      <div className={`h-full rounded-full ${color} transition-[width] duration-300`} style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
    </div>
  );
}

/** 버튼. blocked에 이유를 주면 흐리게 보이고, 누르면 동작 대신 그 이유를 알려 준다
 *  (disabled 버튼은 마우스를 올려도 이유를 보여 줄 수 없고, 휴대폰에선 누를 수도 없어서). */
export function Button({ variant = "default", className = "", blocked, onClick, ...props }) {
  const farm = useFarm();
  const look = {
    default: "bg-card text-ink ring-1 ring-line hover:bg-pressed",
    brand: "bg-brand text-white hover:bg-brand-pressed",
    danger: "bg-card text-critical ring-1 ring-line hover:bg-critical-weak",
    solidDanger: "bg-critical text-white hover:brightness-95",
  }[variant];
  return (
    <button
      {...props}
      aria-disabled={blocked ? true : undefined}
      title={blocked || props.title}
      onClick={blocked ? () => farm?.actions.notice(blocked) : onClick}
      className={`rounded-lg px-3 py-2 text-sm font-medium transition-colors ${look} ${
        blocked ? "cursor-not-allowed opacity-45 hover:brightness-100" : ""
      } ${className}`}
    />
  );
}

/** 작물·구역 상태에 따라 심기·수확·갈아엎기를 왜 못 하는지 (할 수 있으면 null) */
export function actionBlocks(s) {
  const ps = s.plant;
  return {
    plant: ps ? "작물이 남아 있어 심을 수 없어요. 먼저 수확하거나 갈아엎으세요." : null,
    harvest: !ps
      ? "빈 구역이라 수확할 작물이 없어요."
      : ps.alive && !ps.ready
        ? `아직 덜 자랐어요 (${ps.stage}, 생장 ${Math.round(ps.growth)}%).`
        : null,
    plow: ps ? null : "갈아엎을 작물이 없어요.",
  };
}
