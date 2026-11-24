import { useEffect, useState } from "react";
import { useFarm } from "../lib/farm.jsx";
import { num, signedWon } from "../lib/format.js";
import { Button, Card } from "./ui.jsx";

// 입력칸 눈금 (그래프 키별)
const STEP = { temperature: 0.5, humidity: 1, soil: 1, nutrient: 0.1, co2: 10, luminosity: 1000 };

/** 작물 설정: 작물별 적정 조건(자동 제어 기준)을 고친다. 저장하면 지금 자라는 같은 작물에도 바로 적용된다. */
export default function CropSettings() {
  const { meta, state } = useFarm();
  if (!meta) return null;
  return (
    <div>
      <header className="mb-4">
        <h1 className="text-lg font-bold">작물 설정</h1>
        <p className="mt-1 text-sm text-muted">
          장치는 이 적정 범위를 기준으로 켜고 끕니다. 저장하면 그 작물이 자라는 구역과 앞으로 심을 작물에 바로 적용되고, 초기화해도 남습니다.
        </p>
      </header>
      <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
        {meta.crops.map((name) => (
          <CropCard key={name} name={name} crop={state.crops[name]} metrics={meta.metrics} sections={state.sections} />
        ))}
      </div>
    </div>
  );
}

function CropCard({ name, crop, metrics, sections }) {
  const { actions } = useFarm();
  const toDraft = () => Object.fromEntries(metrics.map((m) => [m.key, crop[m.key]]));
  const [draft, setDraft] = useState(toDraft);
  const [busy, setBusy] = useState(false);
  const saved = JSON.stringify(toDraft());
  const dirty = JSON.stringify(draft) !== saved;
  // 서버 값이 바뀌면(다른 화면에서 저장, 기본값으로 되돌림) 고치는 중이 아닐 때만 따라간다
  useEffect(() => {
    if (!dirty) setDraft(JSON.parse(saved));
  }, [saved]); // eslint-disable-line react-hooks/exhaustive-deps

  const errors = Object.fromEntries(
    metrics.map((m) => {
      const [lo, hi] = m.range;
      const v = draft[m.key];
      if (m.key === "luminosity") return [m.key, v >= lo && v <= hi ? null : `${num(lo)}~${num(hi)} 사이로`];
      return [m.key, lo <= v[0] && v[0] < v[1] && v[1] <= hi ? null : `${lo}~${hi} 안에서 하한 < 상한`];
    }),
  );
  const invalid = Object.values(errors).some(Boolean);
  const growing = sections.filter((s) => s.species === name && s.plant).map((s) => s.name);

  const save = async () => {
    setBusy(true);
    await actions.updateCrop(name, draft);
    setBusy(false);
  };

  return (
    <Card
      title={
        <span className="flex items-center gap-2">
          {name}
          {crop.changed && <span className="rounded bg-brand-weak px-1.5 py-0.5 text-[10px] font-bold text-brand-pressed">바뀜</span>}
        </span>
      }
      aside={`재배 ${crop.growDays}일 · 하루 ${signedWon(crop.dailyProfit)}`}
    >
      <p className="-mt-1 mb-3 text-xs text-muted">{growing.length ? `지금 ${growing.join(", ")}에서 자라는 중` : "지금 자라는 구역 없음"}</p>
      <div className="space-y-2">
        {metrics.map((m) => (
          <div key={m.key} className="grid grid-cols-[72px_1fr] items-center gap-2 text-sm">
            <label className="text-muted" htmlFor={`${name}-${m.key}`}>
              {m.title}
            </label>
            <div>
              <div className="flex items-center gap-1.5">
                {m.key === "luminosity" ? (
                  <>
                    <span className="shrink-0 whitespace-nowrap text-xs text-muted">최소</span>
                    <NumberField
                      id={`${name}-${m.key}`}
                      value={draft.luminosity}
                      step={STEP.luminosity}
                      onChange={(v) => setDraft({ ...draft, luminosity: v })}
                      invalid={!!errors.luminosity}
                    />
                  </>
                ) : (
                  [0, 1].map((k) => (
                    <NumberField
                      key={k}
                      id={k ? undefined : `${name}-${m.key}`}
                      label={`${m.title} ${k ? "상한" : "하한"}`}
                      value={draft[m.key][k]}
                      step={STEP[m.key]}
                      onChange={(v) => setDraft({ ...draft, [m.key]: k ? [draft[m.key][0], v] : [v, draft[m.key][1]] })}
                      invalid={!!errors[m.key]}
                    />
                  ))
                )}
                <span className="w-12 shrink-0 text-xs text-muted">{m.unit}</span>
              </div>
              {errors[m.key] && <p className="mt-0.5 text-xs text-critical">{errors[m.key]}</p>}
            </div>
          </div>
        ))}
      </div>
      <div className="mt-4 flex justify-end gap-2">
        {crop.changed && (
          <Button onClick={() => actions.resetCrop(name)} className="text-xs">
            기본값으로
          </Button>
        )}
        <Button onClick={() => setDraft(JSON.parse(saved))} blocked={dirty ? null : "고친 내용이 없어요."} className="text-xs">
          되돌리기
        </Button>
        <Button
          variant="brand"
          onClick={save}
          blocked={!dirty ? "고친 내용이 없어요." : invalid ? "빨간 칸을 먼저 고치세요." : busy ? "저장하는 중이에요." : null}
          className="text-xs"
        >
          저장
        </Button>
      </div>
    </Card>
  );
}

function NumberField({ id, label, value, step, onChange, invalid }) {
  return (
    <input
      id={id}
      aria-label={label}
      aria-invalid={invalid || undefined}
      type="number"
      step={step}
      value={value}
      onChange={(e) => onChange(e.target.value === "" ? NaN : +e.target.value)}
      className={`tabular w-full min-w-0 rounded-md border bg-card px-2 py-1.5 text-sm outline-none focus:border-brand ${
        invalid ? "border-critical" : "border-line"
      }`}
    />
  );
}
