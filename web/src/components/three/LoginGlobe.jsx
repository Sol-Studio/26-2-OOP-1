import { useEffect, useLayoutEffect, useMemo, useRef } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";
import { feature } from "topojson-client";
import land110 from "world-atlas/land-110m.json";
import { useReducedMotion } from "../../lib/motion.js";
import SproutBotModel from "./SproutBotModel.jsx";

const DOTS = 42000; // 구 표면에 고르게 뿌릴 점 후보 수 (그중 육지에 떨어진 것만 그린다)
const FARM = { lat: 36.5, lon: 127.8 }; // 에버그로우 농장 (대한민국)
const TILT = 0.38; // 지축 기울기 느낌
const CENTER = new THREE.Vector3(0, -0.18, 0); // 지구본 중심 (제목과 겹치지 않게 조금 내림)
export const DIVE_SECONDS = 1.8; // 로그인 뒤 농장으로 빨려 들어가는 시간
const easeInOut = (t) => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2);

/** 위도·경도(도) → 반지름 r 구 위의 점 */
function toXYZ(lat, lon, r = 1) {
  const phi = ((90 - lat) * Math.PI) / 180;
  const theta = ((lon + 180) * Math.PI) / 180;
  return new THREE.Vector3(-r * Math.sin(phi) * Math.cos(theta), r * Math.cos(phi), r * Math.sin(phi) * Math.sin(theta));
}

/** 세계 지도(육지)를 정거원통 캔버스에 칠해 두고, 구 위의 점이 육지인지 픽셀로 판정한다. */
function landDots() {
  const W = 1024;
  const H = 512;
  const canvas = document.createElement("canvas");
  canvas.width = W;
  canvas.height = H;
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  ctx.fillStyle = "#fff";
  const land = feature(land110, land110.objects.land);
  for (const f of land.features) {
    const polys = f.geometry.type === "Polygon" ? [f.geometry.coordinates] : f.geometry.coordinates;
    for (const poly of polys) {
      ctx.beginPath();
      for (const ring of poly) {
        ring.forEach(([lon, lat], i) => {
          const x = ((lon + 180) / 360) * W;
          const y = ((90 - lat) / 180) * H;
          if (i) ctx.lineTo(x, y);
          else ctx.moveTo(x, y);
        });
        ctx.closePath();
      }
      ctx.fill("evenodd");
    }
  }
  const pixels = ctx.getImageData(0, 0, W, H).data;
  const golden = Math.PI * (3 - Math.sqrt(5));
  const out = [];
  for (let i = 0; i < DOTS; i++) {
    // 피보나치 구: 점이 구 표면에 고르게 퍼진다
    const y = 1 - (i / (DOTS - 1)) * 2;
    const r = Math.sqrt(1 - y * y);
    const x = Math.cos(golden * i) * r;
    const z = Math.sin(golden * i) * r;
    const lat = (Math.asin(y) * 180) / Math.PI;
    const lon = (Math.atan2(z, -x) * 180) / Math.PI - 180;
    const lonN = ((lon + 540) % 360) - 180;
    const px = Math.min(W - 1, Math.floor(((lonN + 180) / 360) * W));
    const py = Math.min(H - 1, Math.floor(((90 - lat) / 180) * H));
    if (pixels[(py * W + px) * 4] > 128) out.push(new THREE.Vector3(x, y, z));
  }
  return out;
}

/** 로그인 화면 왼쪽: 대륙을 점으로 찍은 지구본이 천천히 돌고, 우리 농장(대한민국) 자리에 표시가 깜빡인다.
 *  dive가 켜지면 카메라가 농장 자리로 빨려 들어가고, 다 들어가면 onDived()를 부른다. */
export default function LoginGlobe({ dive = false, onDived, onLeap, farmScreen, returning = false, botHome = false }) {
  return (
    <Canvas dpr={[1, 2]} camera={{ position: [0, 0, 4.3], fov: 40 }} gl={{ antialias: true, alpha: true }}>
      <ambientLight intensity={0.6} />
      <directionalLight position={[-3, 2, 4]} intensity={1.4} />
      <Globe dive={dive} onDived={onDived} onLeap={onLeap} farmScreen={farmScreen} returning={returning} botHome={botHome} />
    </Canvas>
  );
}

function Globe({ dive, onDived, onLeap, farmScreen, returning, botHome }) {
  const spin = useRef(null);
  const marker = useRef(null);
  const diving = useRef(null); // { t: 0~1, from: 카메라 처음 위치(중심 기준), fov }
  const { camera } = useThree();
  const dots = useRef(null);
  const ring = useRef(null);
  const still = useReducedMotion();
  const points = useMemo(landDots, []);
  const farm = useMemo(() => toXYZ(FARM.lat, FARM.lon, 1.005), []);
  // 처음에 농장이 정면(카메라 쪽)에 오도록 돌려 둔다
  const start = useMemo(() => Math.atan2(-farm.x, farm.z), [farm]);

  useLayoutEffect(() => {
    const m = dots.current;
    const o = new THREE.Object3D();
    points.forEach((p, i) => {
      o.position.copy(p).multiplyScalar(1.003);
      o.lookAt(p.clone().multiplyScalar(2)); // 점 원판이 바깥을 보게
      o.updateMatrix();
      m.setMatrixAt(i, o.matrix);
    });
    m.instanceMatrix.needsUpdate = true;
  }, [points]);

  useEffect(() => {
    if (dive && !diving.current) diving.current = { t: 0, from: camera.position.clone().sub(CENTER), fov: camera.fov };
  }, [dive, camera]);

  const tmp = useMemo(() => ({ farm: new THREE.Vector3(), dir: new THREE.Vector3(), q: new THREE.Quaternion(), look: new THREE.Vector3() }), []);

  useFrame(({ clock }, dt) => {
    const d = diving.current;
    if (d) {
      // 농장 쪽으로 지구 표면을 따라 돌아 들어가면서(구면 보간) 점점 빨라지게 다가간다
      d.t = Math.min(1, d.t + dt / DIVE_SECONDS);
      const e = easeInOut(d.t);
      marker.current.getWorldPosition(tmp.farm);
      const farmDir = tmp.farm.clone().sub(CENTER).normalize();
      const fromDir = d.from.clone().normalize();
      tmp.q.setFromUnitVectors(fromDir, farmDir);
      tmp.dir.copy(fromDir).applyQuaternion(new THREE.Quaternion().slerp(tmp.q, e));
      const dist = THREE.MathUtils.lerp(d.from.length(), 1.02, d.t ** 3);
      camera.position.copy(tmp.dir).multiplyScalar(dist).add(CENTER);
      // 바라보는 곳은 처음 1/3 안에 농장으로 옮겨 두고, 그다음엔 농장 점을 화면 한가운데에 둔 채 들어간다
      camera.lookAt(tmp.look.lerpVectors(CENTER, tmp.farm, 1 - (1 - Math.min(1, d.t / 0.33)) ** 3));
      camera.fov = THREE.MathUtils.lerp(d.fov, 22, e);
      camera.updateProjectionMatrix();
      if (d.t >= 1 && !d.done) {
        d.done = true;
        onDived?.();
      }
    } else if (returning && spin.current) {
      // 새싹봇이 돌아오는 동안 농장이 정면으로 오게 지구를 빠르게 돌린다 (가까운 쪽으로)
      const cur = spin.current.rotation.y;
      const goal = start + Math.PI * 2 * Math.round((cur - start) / (Math.PI * 2));
      spin.current.rotation.y += (goal - cur) * Math.min(1, dt * 4);
    } else if (!still && spin.current) spin.current.rotation.y += dt * 0.12;
    if (ring.current) {
      const t = still ? 0.5 : (clock.elapsedTime * 0.6) % 1;
      ring.current.scale.setScalar(1 + t * 2.5);
      ring.current.material.opacity = 0.9 * (1 - t);
    }
  });

  return (
    <>
    <GlobeBot marker={marker} diving={diving} onLeap={onLeap} farmScreen={farmScreen} botHome={botHome} />
    <group position={CENTER} rotation-x={TILT} rotation-z={-0.12}>
      <group ref={spin} rotation-y={start}>
        {/* 바다 */}
        <mesh>
          <sphereGeometry args={[1, 64, 64]} />
          <meshStandardMaterial color="#17222d" roughness={0.7} metalness={0.1} />
        </mesh>
        {/* 육지 점 */}
        <instancedMesh ref={dots} args={[undefined, undefined, points.length]}>
          <circleGeometry args={[0.0052, 6]} />
          <meshStandardMaterial color="#ff8a3d" emissive="#ff6600" emissiveIntensity={0.55} side={THREE.DoubleSide} />
        </instancedMesh>
        {/* 우리 농장 */}
        <group ref={marker} position={farm} quaternion={new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 0, 1), farm.clone().normalize())}>
          <mesh>
            <circleGeometry args={[0.016, 20]} />
            <meshBasicMaterial color="#ffffff" />
          </mesh>
          <mesh ref={ring} position-z={0.001}>
            <ringGeometry args={[0.016, 0.022, 32]} />
            <meshBasicMaterial color="#ffffff" transparent depthWrite={false} />
          </mesh>
        </group>
      </group>
      <Atmosphere />
    </group>
    </>
  );
}

const BOT_SCALE = 0.15; // 지구 반지름 1에 대한 새싹봇 크기
const HOP = 0.56; // 한 번 뛰는 데 걸리는 시간 (초)
const clamp01 = (v) => Math.min(1, Math.max(0, v));

/** 농장 흰 점 위에서 방방 뛰는 새싹봇. 늘 화면 기준으로 똑바로 서서 이쪽을 보고(지구에 눕지 않게),
 *  착지할 때 찌그러지고, 뛰면 팔을 번쩍 들고, 네 번에 한 번은 공중에서 한 바퀴 돈다.
 *  농장이 지구 뒤로 넘어가면 숨고, 로그인해서 들어갈 때는 신나게 뛰다가 빙글 돌며 농장 속으로 쏙 들어가 앞장선다. */
function GlobeBot({ marker, diving, onLeap, farmScreen, botHome }) {
  const root = useRef(null);
  const inner = useRef(null);
  const parts = useRef({});
  const still = useReducedMotion();
  const leap = useRef({ seen: false, done: false }); // 지구본에서 뛰어내렸는지
  const tmp = useMemo(() => ({ farm: new THREE.Vector3(), normal: new THREE.Vector3(), view: new THREE.Vector3(), screen: new THREE.Vector3() }), []);

  useFrame(({ camera, clock, gl }) => {
    const g = root.current;
    const m = marker.current;
    if (!g || !m || !inner.current) return;
    const d = diving.current;
    const t = clock.elapsedTime;

    // 자리: 흰 점 바로 위, 몸은 카메라를 향해 똑바로
    m.getWorldPosition(tmp.farm);
    tmp.normal.copy(tmp.farm).sub(CENTER).normalize();
    tmp.view.copy(camera.position).sub(tmp.farm).normalize();
    g.position.copy(tmp.farm).addScaledVector(tmp.normal, 0.012);
    g.quaternion.copy(camera.quaternion);
    // 농장이 지구 뒤편이면 숨는다
    const facing = clamp01((tmp.normal.dot(tmp.view) - 0.05) / 0.2);

    // 지구가 돌아 농장이 옆으로 넘어가려 하면, 사라지는 대신 지구본에서 뛰어내려 로그인 창으로 간다.
    // 그 자리(화면 좌표)를 넘겨 주면 화면(DOM)의 새싹봇이 이어받아 날아간다.
    const ls = leap.current;
    const dot = tmp.normal.dot(tmp.view); // 1 = 정면, 0 = 지구 가장자리
    const r = gl.domElement.getBoundingClientRect();
    tmp.screen.copy(g.position).project(camera);
    const screen = { x: r.left + ((tmp.screen.x + 1) / 2) * r.width, y: r.top + ((1 - tmp.screen.y) / 2) * r.height };
    if (farmScreen) farmScreen.current = screen; // 로그인 창에서 돌아올 새싹봇이 노릴 자리
    if (dot > 0.8) ls.seen = true;
    if (!ls.done && ls.seen && !d && !still && onLeap && dot < 0.45) {
      ls.done = true;
      onLeap(screen);
    }
    if (ls.done && botHome) ls.done = false; // 로그인 창에서 다시 뛰어올라 왔다
    if (ls.done) {
      g.scale.setScalar(1e-4);
      return;
    }

    // 들어갈 때: 처음 절반은 두 배로 신나게 뛰고, 그다음 빙글 돌며 작아져 농장 속으로
    const k = d ? d.t : 0;
    const vanish = d ? 1 - clamp01((k - 0.5) / 0.22) : 1;
    g.scale.setScalar(BOT_SCALE * facing * vanish + 1e-4);
    if (still) return;

    const period = d ? HOP / 1.8 : HOP;
    const n = Math.floor(t / period);
    const ph = (t % period) / period;
    const air = Math.sin(Math.PI * ph); // 0(땅) → 1(꼭대기) → 0
    const land = Math.max(0, 1 - air * 5); // 땅에 닿는 순간
    const squash = 1 - 0.28 * land;
    inner.current.position.y = air * (d ? 0.95 : 0.7);
    inner.current.scale.set(1 / Math.sqrt(squash), squash, 1 / Math.sqrt(squash));
    inner.current.rotation.y = d && k > 0.5 ? (k - 0.5) * 40 : n % 4 === 3 ? ph * Math.PI * 2 : Math.sin(t * 1.3) * 0.35;

    const p = parts.current;
    if (p.armL && p.armR) {
      const up = 0.25 + air * 2.3 + (d ? Math.sin(t * 25) * 0.3 : 0);
      p.armL.rotation.z = up;
      p.armR.rotation.z = -up;
    }
    if (p.legL && p.legR) {
      p.legL.rotation.x = -air * 0.7;
      p.legR.rotation.x = -air * 0.7;
    }
    if (p.sprout) p.sprout.rotation.z = Math.sin(t * 16) * 0.3 * land + Math.sin(t * 3) * 0.15;
  });

  return (
    <group ref={root} scale={1e-4}>
      <group ref={inner}>
        <SproutBotModel parts={parts} />
      </group>
    </group>
  );
}

/** 가장자리가 은은하게 빛나는 대기 (프레넬) */
function Atmosphere() {
  const material = useMemo(
    () =>
      new THREE.ShaderMaterial({
        transparent: true,
        depthWrite: false,
        side: THREE.BackSide,
        blending: THREE.AdditiveBlending,
        uniforms: { color: { value: new THREE.Color("#ff7a29") } },
        vertexShader: `
          varying vec3 vNormal;
          varying vec3 vView;
          void main() {
            vec4 mv = modelViewMatrix * vec4(position, 1.0);
            vNormal = normalize(normalMatrix * normal);
            vView = normalize(-mv.xyz);
            gl_Position = projectionMatrix * mv;
          }`,
        fragmentShader: `
          uniform vec3 color;
          varying vec3 vNormal;
          varying vec3 vView;
          void main() {
            float rim = pow(1.0 - abs(dot(vNormal, vView)), 4.0);
            gl_FragColor = vec4(color, rim * 0.45);
          }`,
      }),
    [],
  );
  return (
    <mesh material={material} scale={1.08}>
      <sphereGeometry args={[1, 64, 64]} />
    </mesh>
  );
}
