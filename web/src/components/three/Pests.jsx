import { useLayoutEffect, useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { useReducedMotion } from "../../lib/motion.js";
import { BED_D, BED_W, Particles, SOIL_TOP, rand } from "./Devices.jsx";

const noHit = () => null; // 벌레·안개는 마우스 판정에서 뺀다 (구역 선택·장치 설명을 가리지 않게)

/** 병충해 효과: 흙 위를 기어 다니는 벌레, 작물 위를 맴도는 날벌레 떼.
 *  격리·방제 중(spraying)이면 위에서 약제 안개가 주기적으로 뿌려진다. */
export default function Pests({ spraying }) {
  return (
    <>
      <Crawlers count={16} />
      <Gnats />
      <Spray on={spraying} />
    </>
  );
}

/** 흙 위를 이리저리 기어 다니는 딱정벌레. 방향을 조금씩 틀며 걷다가 가장자리에 닿으면 돌아선다. */
function Crawlers({ count }) {
  const body = useRef(null);
  const head = useRef(null);
  const still = useReducedMotion();
  const o = useMemo(() => new THREE.Object3D(), []);
  const bugs = useMemo(
    () =>
      Array.from({ length: count }, (_, k) => ({
        x: (rand(k * 7 + 1) - 0.5) * BED_W * 0.9,
        z: (rand(k * 7 + 2) - 0.5) * BED_D * 0.9,
        heading: rand(k * 7 + 3) * Math.PI * 2,
        speed: 0.12 + rand(k * 7 + 4) * 0.18, // m/s
        wiggle: rand(k * 7 + 5) * 10,
        size: 0.8 + rand(k * 7 + 6) * 0.5,
      })),
    [count],
  );

  const place = (time) => {
    const halfW = BED_W / 2 - 0.06;
    const halfD = BED_D / 2 - 0.06;
    bugs.forEach((b, i) => {
      const y = SOIL_TOP + 0.012 + Math.abs(Math.sin(time * 18 + b.wiggle)) * 0.004; // 종종걸음
      o.position.set(b.x, y, b.z);
      o.rotation.set(0, -b.heading, 0);
      o.scale.set(0.05 * b.size, 0.022 * b.size, 0.032 * b.size);
      o.updateMatrix();
      body.current.setMatrixAt(i, o.matrix);
      o.position.set(b.x + Math.cos(b.heading) * 0.045 * b.size, y, b.z + Math.sin(b.heading) * 0.045 * b.size);
      o.scale.setScalar(0.016 * b.size);
      o.updateMatrix();
      head.current.setMatrixAt(i, o.matrix);
      if (Math.abs(b.x) > halfW) b.x = Math.sign(b.x) * halfW;
      if (Math.abs(b.z) > halfD) b.z = Math.sign(b.z) * halfD;
    });
    body.current.instanceMatrix.needsUpdate = true;
    head.current.instanceMatrix.needsUpdate = true;
  };

  useLayoutEffect(() => place(0)); // 첫 프레임 전에 자리를 잡아 둔다 (동작 줄이기면 이 자리에 머문다)

  useFrame(({ clock }, dt) => {
    if (still || !body.current) return;
    const step = Math.min(dt, 0.1);
    const halfW = BED_W / 2 - 0.06;
    const halfD = BED_D / 2 - 0.06;
    const t = clock.elapsedTime;
    bugs.forEach((b) => {
      b.heading += Math.sin(t * 1.7 + b.wiggle) * 2.2 * step; // 이리저리 방향을 튼다
      b.x += Math.cos(b.heading) * b.speed * step;
      b.z += Math.sin(b.heading) * b.speed * step;
      if (Math.abs(b.x) > halfW) b.heading = Math.PI - b.heading; // 벽에 닿으면 돌아선다
      if (Math.abs(b.z) > halfD) b.heading = -b.heading;
    });
    place(t);
  });

  return (
    <>
      <instancedMesh ref={body} args={[undefined, undefined, count]} raycast={noHit} castShadow>
        <sphereGeometry args={[1, 10, 8]} />
        <meshStandardMaterial color="#a3361a" emissive="#4a1205" emissiveIntensity={0.4} roughness={0.2} metalness={0.3} />
      </instancedMesh>
      <instancedMesh ref={head} args={[undefined, undefined, count]} raycast={noHit}>
        <sphereGeometry args={[1, 8, 6]} />
        <meshStandardMaterial color="#0f0905" roughness={0.4} />
      </instancedMesh>
    </>
  );
}

/** 작물 위를 맴도는 날벌레 떼: 포기 몇 군데를 중심으로 빙빙 돌며 흔들린다. */
function Gnats() {
  return (
    <Particles
      on
      count={36}
      size={0.014}
      color="#1b130c"
      speed={0.35}
      place={(p, o) => {
        const cx = (Math.floor(p.a * 4) / 3 - 0.5) * BED_W * 0.75; // 무리 4곳
        const cz = (p.c - 0.5) * BED_D * 0.6;
        const a = p.t * Math.PI * 2 * (1 + p.b);
        const r = 0.12 + p.b * 0.18;
        o.position.set(
          cx + Math.cos(a) * r,
          SOIL_TOP + 0.55 + Math.sin(a * 3 + p.c * 9) * 0.12 + p.b * 0.25,
          cz + Math.sin(a * 1.3) * r,
        );
      }}
    />
  );
}

/** 방제: 위에서 옅은 약제 안개를 뿌린다 (뿌렸다 쉬었다). */
function Spray({ on }) {
  return (
    <Particles
      on={on}
      count={60}
      size={0.05}
      color="#e4f7d8"
      opacity={0.32}
      speed={0.5}
      place={(p, o) => {
        const burst = Math.sin(p.t * Math.PI); // 위에서 나와 퍼지며 내려앉는다
        o.position.set((p.a - 0.5) * BED_W * (0.6 + p.t * 0.4), 2.0 - p.t * 1.45, (p.b - 0.5) * BED_D * (0.6 + p.t * 0.4));
        o.scale.setScalar(0.5 + burst * 1.8);
      }}
    />
  );
}
