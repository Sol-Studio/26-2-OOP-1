import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import * as THREE from "three";
import { useFarm } from "../../lib/farm.jsx";
import { MODE_NAMES, TONE_BG, TONE_TEXT, clock, deviceLabel, deviceOn, num, signedWon } from "../../lib/format.js";
import { useReducedMotion } from "../../lib/motion.js";
import { BURST_SECONDS } from "./HarvestBurst.jsx";
import Zone, { LABEL_OFFSET, zonePosition } from "./Zone.jsx";

const OVERVIEW = { pos: [0, 12, 15.5], target: [0, 0.3, 0.8] };
// 첫 화면 연출: 온실 단지 바로 위 하늘에서 수직으로 내려온 뒤(DROP) 평소 각도로 기울어진다(TILT)
const INTRO = { sky: 70, low: 19, drop: 1.6, tilt: 1.1 };
const easeOut = (t) => 1 - (1 - t) ** 3;
const easeInOut = (t) => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2);
const NIGHT_SKY = new THREE.Color("#0d1620");
const CLEAR_SKY = new THREE.Color("#bcd9ee");
const CLOUDY_SKY = new THREE.Color("#b4bec7");

// 카메라 이동 키 (KeyboardEvent.code). Q·E는 아래·위, Shift를 누르면 빠르게.
const MOVE_KEYS = new Set([
  "KeyW", "KeyA", "KeyS", "KeyD", "KeyQ", "KeyE",
  "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "ShiftLeft", "ShiftRight",
]);

/** 온실 3D 화면. 구역마다 온실 한 동씩, 작물 상태(생장·건강·병충해)와 격리·장치 8개의 동작을 3D로 보여 준다.
 *  구역을 고르면 카메라가 그 온실로 날아가 가까이 보여 준다. 화면을 누른 뒤 WASD로 움직인다.
 *  focus면 늘 선택한 구역을 가까이 본다 (모바일 CCTV 탭).
 *  intro면 카메라가 하늘에서 수직으로 내려와 제자리로 가고, 끝나면 onIntroDone()을 부른다 (로그인 직후 첫 화면). */
export default function Greenhouse3D({ focus = false, compact = false, intro = false, onIntroDone }) {
  const { state, selected, select, user } = useFarm();
  const s = state.sections[selected];
  const labels = useRef([]);
  const tip = useRef(null);
  const [hoverDevice, setHoverDevice] = useState(null); // { zone, key } — 마우스가 올라간 장치
  // held: 누르고 있는 키, taps: 다음 프레임 전에 눌렸다 떼어진 키도 한 번은 움직이게
  const keys = useRef({ held: new Set(), taps: new Set() });
  const [overview, setOverview] = useState(!focus);
  const [shot, setShot] = useState(0); // 카메라 이동 요청 번호: 같은 구역을 다시 골라도 다시 날아가게
  const zoomed = focus || !overview;
  const [introRunning, setIntroRunning] = useState(intro);
  const bursts = useHarvestBursts(state.harvestEvents, state.sections);
  const tags = useRef(new Map()); // 수확 금액 표시 div (연출 id → 요소)

  const flyTo = useCallback(() => {
    setOverview(false);
    setShot((n) => n + 1);
  }, []);

  // 카드·모바일 목록 등 다른 곳에서 구역을 바꿔도 카메라가 따라간다 (처음 그릴 때는 제외)
  const first = useRef(true);
  useEffect(() => {
    if (first.current) first.current = false;
    else flyTo();
  }, [selected, flyTo]);

  const pick = (i) => {
    select(i);
    flyTo();
  };

  const onKey = (down) => (e) => {
    if (!MOVE_KEYS.has(e.code)) return;
    e.preventDefault();
    const { held, taps } = keys.current;
    if (down) {
      held.add(e.code);
      taps.add(e.code);
    } else held.delete(e.code);
  };

  return (
    <div
      tabIndex={0}
      aria-label="온실 3D 화면. 누른 뒤 W A S D로 이동"
      onPointerDown={(e) => e.currentTarget.focus()}
      onKeyDown={onKey(true)}
      onKeyUp={onKey(false)}
      onBlur={() => keys.current.held.clear()}
      onPointerMove={(e) => {
        // 장치 설명 말풍선이 마우스를 따라다니게 (다시 그리지 않고 위치만 옮긴다)
        const box = e.currentTarget.getBoundingClientRect();
        if (tip.current) tip.current.style.transform = `translate(${e.clientX - box.left + 14}px, ${e.clientY - box.top + 14}px)`;
      }}
      onPointerLeave={() => setHoverDevice(null)}
      className="relative h-full w-full bg-dark outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-brand"
    >
      <Canvas shadows dpr={[1, 2]} camera={{ position: OVERVIEW.pos, fov: 38 }}>
        <Scene state={state} selected={selected} pick={pick} onHoverDevice={setHoverDevice} bursts={bursts} />
        <CameraRig
          zoomed={zoomed}
          selected={selected}
          shot={shot}
          keys={keys}
          intro={intro}
          onIntroDone={() => {
            setIntroRunning(false);
            onIntroDone?.();
          }}
        />
        <LabelTracker labels={labels} count={state.sections.length} />
        <HarvestTagTracker tags={tags} bursts={bursts} />
      </Canvas>

      {/* 구역 이름표: 3D 위치를 매 프레임 화면 좌표로 바꿔 옮긴다 */}
      <div className={`pointer-events-none absolute inset-0 overflow-hidden transition-opacity duration-500 ${introRunning ? "opacity-0" : ""}`}>
        {state.sections.map((sec) => {
          const on = sec.index === selected;
          // 전체 보기에서 고르지 않은 구역은 이름과 상태 점만 작게 (뒷줄 이름표가 앞줄 온실을 가리지 않게)
          const small = !zoomed && !on;
          return (
            <div
              key={sec.index}
              ref={(el) => (labels.current[sec.index] = el)}
              hidden={zoomed && !on} // 가까이 볼 때는 다른 온실 이름표가 가리지 않게
              title={small ? `${sec.label} · ${sec.status.label}` : undefined}
              className={`absolute left-0 top-0 whitespace-nowrap rounded-md text-center shadow ${
                on ? "bg-brand px-2 py-1 text-xs text-white" : small ? "bg-card/85 px-1.5 py-0.5 text-[11px] text-ink" : "bg-card/90 px-2 py-1 text-xs text-ink"
              }`}
            >
              {small ? (
                <span className="flex items-center gap-1 font-bold">
                  <span className={`size-2 rounded-full ${TONE_BG[sec.status.tone]}`} aria-hidden />
                  {sec.name}
                  {sec.status.tone === "critical" || sec.status.tone === "dead" ? <span className="text-critical">!</span> : null}
                </span>
              ) : (
                <>
                  <div className="font-bold">{sec.label}</div>
                  <div className={`text-[11px] font-bold ${on ? "text-white" : TONE_TEXT[sec.status.tone]}`}>{sec.status.label}</div>
                </>
              )}
            </div>
          );
        })}
      </div>

      {hoverDevice && <DeviceTip tipRef={tip} hover={hoverDevice} sections={state.sections} />}

      {/* 수확 금액: 그 온실 위로 떠오르다 사라진다 (위치는 HarvestTagTracker가 매 프레임 옮긴다) */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        {bursts.map((b) => (
          <div
            key={b.id}
            ref={(el) => (el ? tags.current.set(b.id, el) : tags.current.delete(b.id))}
            style={{ opacity: 0 }}
            className="absolute left-0 top-0 whitespace-nowrap rounded-xl bg-dark/85 px-3.5 py-2 text-center shadow-lg ring-1 ring-[#ffd36b]/50"
          >
            <p className="text-[11px] text-dark-text">
              {b.zone} {b.crop} 수확
            </p>
            <p className="tabular text-2xl font-bold text-[#ffd36b]">+{num(b.revenue)}원</p>
            <p className="tabular text-[11px] text-dark-text">
              {b.kg.toFixed(1)}kg · 품질 {Math.round(b.quality)}% · 순이익{" "}
              <b className={b.profit >= 0 ? "text-[#5fe0a8]" : "text-[#ff7b74]"}>{signedWon(b.profit)}</b>
            </p>
          </div>
        ))}
      </div>

      {/* 첫 화면 연출(카메라 강하) 동안 가운데에 크게 띄우는 인사 */}
      {intro && (
        <div
          aria-live="polite"
          className={`pointer-events-none absolute inset-0 z-10 grid place-items-center transition-opacity duration-700 ${introRunning ? "" : "opacity-0"}`}
        >
          <div className="animate-[welcome_1.2s_ease-out_both] text-center text-white [text-shadow:0_2px_24px_rgb(0_0_0/0.55)]">
            <p className="text-6xl font-bold tracking-tight sm:text-7xl">환영합니다</p>
            <p className="mt-4 text-lg font-medium text-white/85">{user}님, 에버그로우 농장에 오신 것을 환영합니다</p>
          </div>
        </div>
      )}

      {/* CCTV 느낌의 겉모습: 녹화 표시, 카메라 이름, 시각 */}
      <div className="pointer-events-none absolute inset-x-0 top-0 flex items-center justify-between gap-3 p-3 font-mono text-xs font-bold text-white [text-shadow:0_1px_2px_rgb(0_0_0/0.6)]">
        <span className="flex items-center gap-1.5">
          <span className="size-2 rounded-full bg-critical motion-safe:animate-pulse" />
          <span className="text-critical">REC</span>
        </span>
        <span>{zoomed ? `CAM ${String(selected + 1).padStart(2, "0")} · ${s.label}` : "CAM 00 · 온실 전체"}</span>
      </div>
      {!focus && !introRunning && (
        <button
          onClick={() => (zoomed ? setOverview(true) : flyTo())}
          className="absolute left-3 top-9 rounded-md bg-card/90 px-2.5 py-1 font-sans text-xs font-bold text-ink shadow hover:bg-card"
        >
          {zoomed ? "← 전체 보기" : `${s.label} 가까이 보기`}
        </button>
      )}
      <div className="pointer-events-none absolute inset-x-0 bottom-0 flex items-end justify-between p-3 text-xs text-white [text-shadow:0_1px_2px_rgb(0_0_0/0.6)]">
        <span className="font-mono font-bold">
          Day{state.day} {clock(state.hour)}
        </span>
        {!compact && <span className="opacity-80">드래그 돌리기 · 휠 확대 · 누른 뒤 WASD 이동 (Q·E 아래·위, Shift 빠르게)</span>}
      </div>
    </div>
  );
}

function Scene({ state, selected, pick, onHoverDevice, bursts }) {
  const { weather, hour } = state;
  const daylight = Math.min(1, (weather.sunlight / 80000) * 1.8);
  const sky = useMemo(
    () => NIGHT_SKY.clone().lerp(weather.cloud > 0.5 ? CLOUDY_SKY : CLEAR_SKY, daylight),
    [daylight, weather.cloud],
  );
  // 해는 6시에 동쪽(+x)에서 떠서 18시에 서쪽으로 진다. 밤에는 달빛 정도만 남긴다.
  const angle = (Math.PI * (hour - 6)) / 12;
  const sunPos = [Math.cos(angle) * 20, Math.max(Math.sin(angle), 0.2) * 20, 10];

  return (
    <>
      <color attach="background" args={[sky]} />
      <fog attach="fog" args={[sky, 30, 70]} />
      <hemisphereLight args={["#e4f1ff", "#3d3226", 0.6 + 0.6 * daylight]} />
      <directionalLight
        position={sunPos}
        intensity={0.12 + 2.4 * daylight}
        color={daylight > 0.05 ? "#fff3dc" : "#8ea6d6"}
        castShadow
        shadow-mapSize={[2048, 2048]}
        shadow-camera-left={-16}
        shadow-camera-right={16}
        shadow-camera-top={16}
        shadow-camera-bottom={-16}
        shadow-bias={-0.0005}
      />

      <mesh rotation-x={-Math.PI / 2} position-y={-0.01} receiveShadow>
        <planeGeometry args={[120, 120]} />
        <meshStandardMaterial color="#6e7c5c" roughness={1} />
      </mesh>
      {state.sections.map((s) => (
        <Zone
          key={s.index}
          section={s}
          position={zonePosition(s.index)}
          selected={s.index === selected}
          onSelect={() => pick(s.index)}
          onHoverDevice={onHoverDevice}
          bursts={bursts.filter((b) => b.index === s.index)}
        />
      ))}

    </>
  );
}

// WASD로 움직일 수 있는 범위 (보는 지점 기준)
const BOUNDS = { x: 18, z: 14, y: [0, 6] };

/** 카메라: 구역을 고를 때마다 그 온실로 부드럽게 날아가고, 그다음엔 마우스로 돌리거나 WASD로 움직인다.
 *  WASD는 보는 방향 기준 앞·뒤·옆으로, 카메라와 보는 지점을 함께 옮긴다. */
function CameraRig({ zoomed, selected, shot, keys, intro, onIntroDone }) {
  const controls = useRef(null);
  const { camera, scene } = useThree();
  const remaining = useRef(intro ? 0 : 1);
  const introT = useRef(intro ? 0 : null); // 첫 화면 연출 진행 시간(초), 끝나면 null
  const [introOn, setIntroOn] = useState(intro);
  const still = useReducedMotion();
  const v = useMemo(() => ({ fwd: new THREE.Vector3(), right: new THREE.Vector3(), move: new THREE.Vector3() }), []);
  const goal = useMemo(() => {
    if (!zoomed) return { pos: new THREE.Vector3(...OVERVIEW.pos), target: new THREE.Vector3(...OVERVIEW.target) };
    const [x, , z] = zonePosition(selected);
    return { pos: new THREE.Vector3(x + 4.2, 5.4, z + 8), target: new THREE.Vector3(x, 1, z) };
  }, [zoomed, selected, shot]); // shot이 바뀌면 같은 곳이라도 다시 날아간다

  useEffect(() => {
    if (introT.current == null) remaining.current = 1;
  }, [goal]);

  // 첫 프레임을 그리기 전에 카메라를 하늘 위에 둔다 (평소 자리가 한 번 비치지 않게)
  useLayoutEffect(() => {
    if (intro) camera.position.set(0, INTRO.sky, 0.01);
  }, [intro, camera]);

  useFrame((_, dt) => {
    const c = controls.current;
    if (!c) return;
    if (scene.fog) {
      const h = camera.position.length();
      scene.fog.near = Math.max(30, h * 1.1);
      scene.fog.far = Math.max(70, h * 2.2);
    }
    if (introT.current != null) {
      const t = (introT.current += dt);
      if (t < INTRO.drop) {
        // 1) 수직 낙하: 바로 아래를 내려다보며 높이만 줄인다
        const y = THREE.MathUtils.lerp(INTRO.sky, INTRO.low, easeOut(t / INTRO.drop));
        camera.position.set(0, y, 0.01);
        c.target.set(0, 0, 0);
      } else {
        // 2) 평소 각도로 기울며 제자리로
        const k = easeInOut(Math.min(1, (t - INTRO.drop) / INTRO.tilt));
        camera.position.lerpVectors(new THREE.Vector3(0, INTRO.low, 0.01), new THREE.Vector3(...OVERVIEW.pos), k);
        c.target.lerpVectors(new THREE.Vector3(0, 0, 0), new THREE.Vector3(...OVERVIEW.target), k);
        if (k >= 1) {
          introT.current = null;
          setIntroOn(false);
          onIntroDone?.();
        }
      }
      c.update();
      return;
    }
    const { held, taps } = keys.current;
    if (held.size || taps.size) {
      const k = new Set([...held, ...taps]);
      const step = held.size ? dt : Math.max(dt, 1 / 20); // 톡 누른 키는 최소 한 걸음
      taps.clear();
      const { fwd, right, move } = v;
      camera.getWorldDirection(fwd);
      fwd.y = 0;
      fwd.normalize();
      right.crossVectors(fwd, camera.up).normalize();
      move.set(0, 0, 0);
      if (k.has("KeyW") || k.has("ArrowUp")) move.add(fwd);
      if (k.has("KeyS") || k.has("ArrowDown")) move.sub(fwd);
      if (k.has("KeyD") || k.has("ArrowRight")) move.add(right);
      if (k.has("KeyA") || k.has("ArrowLeft")) move.sub(right);
      if (move.lengthSq()) move.normalize();
      move.y = (k.has("KeyE") ? 1 : 0) - (k.has("KeyQ") ? 1 : 0);
      if (move.lengthSq()) {
        move.multiplyScalar((k.has("ShiftLeft") || k.has("ShiftRight") ? 16 : 6) * step);
        // 온실 단지 밖으로 멀리 나가지 않게 보는 지점을 범위 안에 묶는다
        const t = c.target;
        move.x = THREE.MathUtils.clamp(t.x + move.x, -BOUNDS.x, BOUNDS.x) - t.x;
        move.z = THREE.MathUtils.clamp(t.z + move.z, -BOUNDS.z, BOUNDS.z) - t.z;
        move.y = THREE.MathUtils.clamp(t.y + move.y, ...BOUNDS.y) - t.y;
        camera.position.add(move);
        t.add(move);
        remaining.current = 0; // 직접 움직이면 자동 이동은 멈춘다
        c.update();
      }
    }
    if (remaining.current <= 0) return;
    const a = still ? 1 : 1 - Math.exp(-dt * 5);
    camera.position.lerp(goal.pos, a);
    c.target.lerp(goal.target, a);
    c.update();
    remaining.current -= dt / 1.2;
  });

  return (
    <OrbitControls
      ref={controls}
      makeDefault
      enabled={!introOn}
      enablePan={false}
      minDistance={3}
      maxDistance={36}
      maxPolarAngle={Math.PI / 2.15}
      onStart={() => (remaining.current = 0)}
    />
  );
}

/** 이름표 div들을 각 온실 앞쪽 바닥 위치에 맞춰 옮긴다. 카메라 뒤로 가면 숨긴다. */
function LabelTracker({ labels, count }) {
  const v = useMemo(() => new THREE.Vector3(), []);
  useFrame(({ camera, size }) => {
    for (let i = 0; i < count; i++) {
      const el = labels.current[i];
      if (!el) continue;
      const [x, y, z] = zonePosition(i);
      v.set(x + LABEL_OFFSET[0], y + LABEL_OFFSET[1], z + LABEL_OFFSET[2]).project(camera);
      const sx = ((v.x + 1) / 2) * size.width;
      const sy = ((1 - v.y) / 2) * size.height;
      el.style.transform = `translate(${sx}px, ${sy}px) translate(-50%, -50%)`;
      el.style.visibility = v.z > 1 ? "hidden" : "visible";
    }
  });
  return null;
}

/** 장치 설명 말풍선: 이름, 켜짐, 운전 방식(자동/수동), 지금 그 상태인 이유 */
function DeviceTip({ tipRef, hover, sections }) {
  const { meta } = useFarm();
  const sec = sections[hover.zone];
  const d = sec.devices;
  const on = deviceOn(hover.key, d);
  const mode = d.modes[hover.key];
  const label = meta?.devices.find((x) => x.key === hover.key)?.label ?? hover.key;
  const reason = !sec.plant?.alive ? "작물이 없어 멈춤" : d.reasons[hover.key] || (on ? "자동 운전 중" : "적정 범위 안 · 대기");
  return (
    <div
      ref={tipRef}
      role="tooltip"
      className="pointer-events-none absolute left-0 top-0 z-10 w-56 rounded-lg bg-dark/95 p-2.5 text-xs text-dark-text shadow-lg"
    >
      <p className="flex items-center justify-between gap-2">
        <b className="text-sm text-white">{deviceLabel(hover.key, label, d)}</b>
        <span className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${on ? "bg-brand text-white" : "bg-dark-2"}`}>{on ? "● 켜짐" : "○ 꺼짐"}</span>
      </p>
      <p className="mt-1 text-subtle">
        {sec.label} · {mode === "auto" ? "자동" : `수동 ${MODE_NAMES[mode]}`}
      </p>
      <p className="mt-1">{reason}</p>
    </div>
  );
}

/** 서버가 보낸 최근 수확 중 새로 생긴 것만 연출 목록에 넣고, 연출 시간이 지나면 뺀다.
 *  처음 접속했을 때 이미 있던 수확은 연출하지 않는다. */
function useHarvestBursts(events = [], sections) {
  const [bursts, setBursts] = useState([]);
  const last = useRef(null);
  useEffect(() => {
    const newest = events.at(-1)?.id ?? 0;
    if (last.current == null) {
      last.current = newest;
      return;
    }
    const fresh = events.filter((e) => e.id > last.current);
    last.current = Math.max(last.current, newest);
    if (!fresh.length) return;
    const born = performance.now();
    const added = fresh.map((e) => ({ ...e, index: sections.findIndex((s) => s.name === e.zone), born }));
    setBursts((b) => [...b, ...added]);
    const ids = new Set(added.map((e) => e.id));
    setTimeout(() => setBursts((b) => b.filter((e) => !ids.has(e.id))), BURST_SECONDS * 1000);
  }, [events, sections]);
  return bursts;
}

/** 수확 금액 표시를 그 온실 위 공중에 맞춰 옮긴다. 시간이 지나며 떠오르고, 끝에 사라진다. */
function HarvestTagTracker({ tags, bursts }) {
  const v = useMemo(() => new THREE.Vector3(), []);
  useFrame(({ camera, size }) => {
    const now = performance.now();
    for (const b of bursts) {
      const el = tags.current.get(b.id);
      if (!el || b.index < 0) continue;
      const age = (now - b.born) / 1000;
      const [x, , z] = zonePosition(b.index);
      v.set(x, 3.0 + (1 - (1 - Math.min(1, age / 2.6)) ** 3) * 1.8, z).project(camera);
      // 화면 밖으로 잘리지 않게 3D 화면 가장자리 안쪽으로 붙잡는다 (뒷줄 온실은 위로 떠오르다 위가 잘렸다)
      const halfW = el.offsetWidth / 2 + 8;
      const sx = Math.min(size.width - halfW, Math.max(halfW, ((v.x + 1) / 2) * size.width));
      const sy = Math.min(size.height - 8, Math.max(el.offsetHeight + 36, ((1 - v.y) / 2) * size.height));
      const appear = Math.min(1, age / 0.35);
      const vanish = Math.min(1, Math.max(0, (BURST_SECONDS - age) / 0.6));
      el.style.transform = `translate(${sx}px, ${sy}px) translate(-50%, -100%) scale(${0.85 + 0.15 * appear})`;
      el.style.opacity = v.z > 1 ? 0 : Math.min(appear, vanish);
    }
  });
  return null;
}
