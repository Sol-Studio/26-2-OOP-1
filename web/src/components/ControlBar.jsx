import { useFarm } from "../lib/farm.jsx";
import { signedWon } from "../lib/format.js";
import { Button, actionBlocks } from "./ui.jsx";

/** 선택 구역 조작: 작물 고르기(추천 포함), 심기·수확·갈아엎기, 일괄 수확, 자동 재파종 */
export default function ControlBar() {
  const { state, meta, selected, crop, setCrop, actions } = useFarm();
  const s = state.sections[selected];
  const ps = s.plant;
  const block = actionBlocks(s);
  const crops = state.crops;
  // 지금 시세로 심었을 때 하루당 예상 순이익이 가장 큰 작물
  const best = meta?.crops.reduce((a, b) => (crops[b].dailyProfit > crops[a].dailyProfit ? b : a));
  const anyReady = state.sections.some((x) => x.plant?.ready);

  return (
    <div className="rounded-xl bg-card p-3 ring-1 ring-line">
      <div className="flex flex-wrap items-center gap-2">
        <label className="flex items-center gap-2 text-sm">
          <span className="text-muted">작물</span>
          <select
            value={crop}
            onChange={(e) => setCrop(e.target.value)}
            className="rounded-lg border border-line bg-card px-2.5 py-2 text-sm outline-none focus:border-brand"
          >
            {meta?.crops.map((c) => (
              <option key={c} value={c}>
                {c} · 하루 {signedWon(crops[c].dailyProfit)}
                {c === best ? " (추천)" : ""}
              </option>
            ))}
          </select>
        </label>
        <Button variant="brand" onClick={() => actions.plant(selected, crop)} blocked={block.plant}>
          심기
        </Button>
        <Button onClick={() => actions.harvest(selected)} blocked={block.harvest}>
          {ps && !ps.alive ? "정리" : "수확"}
        </Button>
        <Button variant="danger" onClick={() => actions.plow(selected)} blocked={block.plow}>
          갈아엎기
        </Button>
        <span className="mx-1 hidden h-6 w-px bg-line sm:block" />
        <Button onClick={actions.harvestAll} blocked={anyReady ? null : "수확 가능한 구역이 없어요."}>
          수확 가능한 구역 모두 수확
        </Button>
      </div>

      <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-sm">
        {best && (
          <button
            onClick={() => setCrop(best)}
            className="rounded-md bg-brand-weak px-2.5 py-1 text-xs text-brand-pressed ring-1 ring-brand/30 hover:ring-brand"
            title="지금 시세와 지금까지 쓴 비용으로 계산한 하루당 예상 순이익이 가장 큰 작물"
          >
            추천 <b>{best}</b> · 하루 {signedWon(crops[best].dailyProfit)} {crop !== best && "→ 고르기"}
          </button>
        )}
        <label className="flex cursor-pointer items-center gap-2 text-muted">
          <input
            type="checkbox"
            checked={state.autoReplant}
            onChange={(e) => actions.setSim({ autoReplant: e.target.checked })}
            className="size-4 accent-brand"
          />
          수확 후 자동 재파종 (추천 작물)
        </label>
      </div>
    </div>
  );
}
