import { useEffect, useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { SOIL_TOP, rand } from "./Devices.jsx";

export const BURST_SECONDS = 3.4; // 수확 연출 길이

const noHit = () => null;
const easeOut = (t) => 1 - (1 - t) ** 3;
const clamp01 = (v) => Math.min(1, Math.max(0, v));

// 솟아오를 작물 자리 4 × 3 (심은 자리와 같다)
const SPOTS = [];
for (const z of [-0.72, 0, 0.72]) for (const x of [-1.14, -0.38, 0.38, 1.14]) SPOTS.push([x, z]);

// 작물별 모양: [{ 도형, 색 이름, 위치, 크기 }] — 색은 아래 COLORS에서 (서서히 사라지게 재질을 같이 쓴다)
const SHAPES = {
  상추: [
    { geo: "sphere", color: "leaf", pos: [0, 0, 0], scale: [0.11, 0.07, 0.11] },
    { geo: "sphere", color: "leafLight", pos: [0.05, 0.03, 0.02], scale: [0.07, 0.05, 0.07] },
    { geo: "sphere", color: "leafLight", pos: [-0.05, 0.03, -0.02], scale: [0.07, 0.05, 0.07] },
  ],
  시금치: [
    { geo: "sphere", color: "leafDark", pos: [0, 0, 0], scale: [0.09, 0.06, 0.09] },
    { geo: "sphere", color: "leafDark", pos: [0.05, 0.04, 0], scale: [0.06, 0.03, 0.04] },
    { geo: "sphere", color: "leafDark", pos: [-0.05, 0.04, 0], scale: [0.06, 0.03, 0.04] },
  ],
  토마토: [
    { geo: "sphere", color: "tomato", pos: [0, 0, 0], scale: [0.095, 0.085, 0.095] },
    { geo: "cone", color: "stem", pos: [0, 0.085, 0], scale: [0.045, 0.02, 0.045] },
  ],
  딸기: [
    { geo: "cone", color: "berry", pos: [0, -0.02, 0], scale: [0.07, -0.12, 0.07] },
    { geo: "cone", color: "stem", pos: [0, 0.045, 0], scale: [0.055, 0.02, 0.055] },
  ],
  파프리카: [
    { geo: "sphere", color: "paprika", pos: [0, 0, 0], scale: [0.1, 0.11, 0.1] },
    { geo: "cylinder", color: "stem", pos: [0, 0.12, 0], scale: [0.012, 0.04, 0.012] },
  ],
  오이: [{ geo: "cylinder", color: "cucumber", pos: [0, 0, 0], scale: [0.035, 0.26, 0.035], rot: [0, 0, 1.2] }],
};
const COLORS = {
  leaf: "#3f9b4c", leafLight: "#7cc66a", leafDark: "#1f6b34", tomato: "#e0392b", berry: "#e0405a",
  paprika: "#f2a20c", cucumber: "#3f8a2e", stem: "#2f7d2a",
};
const GEOS = {
  sphere: new THREE.SphereGeometry(1, 16, 12),
  cone: new THREE.ConeGeometry(1, 1, 14),
  cylinder: new THREE.CylinderGeometry(1, 1, 1, 12),
};

/** 수확 연출: 수확한 작물이 흙에서 솟아올라 돌며 지붕 위로 떠오르고, 금빛 반짝이가 흩어진 뒤 사라진다. */
export default function HarvestBurst({ species }) {
  const items = useRef([]);
  const sparks = useRef(null);
  const born = useRef(null);
  const o = useMemo(() => new THREE.Object3D(), []);
  const shape = SHAPES[species] ?? SHAPES.토마토;
  // 연출 하나가 쓰는 재질 (같이 투명해지게). 끝나면 버린다.
  const mats = useMemo(
    () => Object.fromEntries(Object.entries(COLORS).map(([k, c]) => [k, new THREE.MeshStandardMaterial({ color: c, roughness: 0.45, transparent: true })])),
    [],
  );
  const gold = useMemo(() => new THREE.MeshStandardMaterial({ color: "#ffd36b", emissive: "#ffb21f", emissiveIntensity: 1.2, transparent: true }), []);
  useEffect(
    () => () => {
      Object.values(mats).forEach((m) => m.dispose());
      gold.dispose();
    },
    [mats, gold],
  );
  const sparkData = useMemo(
    () => Array.from({ length: 28 }, (_, k) => ({ vx: (rand(k * 3 + 11) - 0.5) * 1.6, vz: (rand(k * 3 + 12) - 0.5) * 1.2, vy: 2.2 + rand(k * 3 + 13) * 1.6 })),
    [],
  );

  useFrame(({ clock }) => {
    if (born.current == null) born.current = clock.elapsedTime;
    const t = clock.elapsedTime - born.current;
    const fade = t < 2.3 ? 1 : clamp01(1 - (t - 2.3) / 0.9);
    Object.values(mats).forEach((m) => (m.opacity = fade));
    gold.opacity = clamp01(1 - t / 1.6);

    items.current.forEach((g, k) => {
      if (!g) return;
      const u = clamp01((t - k * 0.05) / 2.4); // 포기마다 조금씩 늦게
      const [x, z] = SPOTS[k];
      const pop = u < 0.12 ? (u / 0.12) * 1.3 : 1.3 - Math.min(1, (u - 0.12) / 0.12) * 0.3; // 툭 튀어나오기
      g.position.set(x * (1 - u * 0.35), SOIL_TOP + 0.05 + easeOut(u) * 3.4, z * (1 - u * 0.35));
      g.rotation.set(Math.sin(u * 6 + k) * 0.3, u * 7 + k, 0);
      g.scale.setScalar(Math.max(0.001, pop));
    });

    const m = sparks.current;
    if (m) {
      sparkData.forEach((s, i) => {
        const tt = Math.min(t, 1.6);
        o.position.set(s.vx * tt, SOIL_TOP + 0.2 + s.vy * tt - 1.6 * tt * tt, s.vz * tt);
        o.scale.setScalar(0.03 * (1 - tt / 1.8));
        o.updateMatrix();
        m.setMatrixAt(i, o.matrix);
      });
      m.instanceMatrix.needsUpdate = true;
    }
  });

  return (
    <group>
      {SPOTS.map((_, k) => (
        <group key={k} ref={(el) => (items.current[k] = el)} scale={0.001}>
          {shape.map((p, j) => (
            <mesh key={j} geometry={GEOS[p.geo]} material={mats[p.color]} position={p.pos} scale={p.scale} rotation={p.rot ?? [0, 0, 0]} raycast={noHit} castShadow />
          ))}
        </group>
      ))}
      <instancedMesh ref={sparks} args={[GEOS.sphere, gold, sparkData.length]} raycast={noHit} frustumCulled={false} />
      {/* 흙에서 순간 번쩍 */}
      <Flash />
    </group>
  );
}

/** 흙 위에서 금빛 원이 퍼지며 번쩍인다. (빛을 새로 켜면 셰이더를 다시 만들어 멈칫하므로 빛 대신 원판으로) */
function Flash() {
  const ref = useRef(null);
  const born = useRef(null);
  useFrame(({ clock }) => {
    if (born.current == null) born.current = clock.elapsedTime;
    const t = clock.elapsedTime - born.current;
    const m = ref.current;
    if (!m) return;
    m.scale.setScalar(0.3 + easeOut(Math.min(1, t / 0.9)) * 2.2);
    m.material.opacity = Math.max(0, 0.8 * (1 - t / 0.9));
  });
  return (
    <mesh ref={ref} position-y={SOIL_TOP + 0.02} rotation-x={-Math.PI / 2} raycast={noHit}>
      <ringGeometry args={[0.55, 0.75, 48]} />
      <meshBasicMaterial color="#ffd36b" transparent depthWrite={false} blending={THREE.AdditiveBlending} />
    </mesh>
  );
}
