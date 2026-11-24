import { useMemo, useState } from "react";
import { Edges, useCursor } from "@react-three/drei";
import * as THREE from "three";
import Devices, { BED_D, BED_W, SOIL_TOP } from "./Devices.jsx";
import House, { GH } from "./House.jsx";
import { useReducedMotion } from "../../lib/motion.js";
import HarvestBurst from "./HarvestBurst.jsx";
import Pests from "./Pests.jsx";
import Plant from "./Plant.jsx";

/** 구역 i의 온실 위치: 온실 6동을 3열 × 2줄로 둔다 */
export function zonePosition(i) {
  const col = i % 3;
  const row = Math.floor(i / 3);
  return [(col - 1) * (GH.w + 1.2), 0, (row - 0.5) * (GH.d + 1.4)];
}
export const LABEL_OFFSET = [0, 0.05, GH.d / 2 + 0.45]; // 이름표 자리: 온실 앞쪽 바닥

// 한 구역에 심긴 포기 자리 4 × 3
const SPOTS = [];
for (const z of [-0.72, 0, 0.72]) for (const x of [-1.14, -0.38, 0.38, 1.14]) SPOTS.push([x, z]);

const DRY = new THREE.Color("#8d6c4b");
const WET = new THREE.Color("#4a3423");

/** 구역 하나 = 온실 한 동: 온실, 흙, 작물, 장치 8개. 온실 어디를 눌러도 그 구역이 선택된다. */
export default function Zone({ section: s, position, selected, onSelect, onHoverDevice, bursts = [] }) {
  const [hover, setHover] = useState(false);
  const still = useReducedMotion();
  useCursor(hover);
  const ps = s.plant;
  const soil = s.env[2]; // 토양 습도 %
  const soilColor = useMemo(() => DRY.clone().lerp(WET, Math.min(1, soil / 90)), [soil]);
  const leafy = s.stages.length <= 4;

  return (
    <group
      position={position}
      onClick={(e) => {
        e.stopPropagation();
        if (e.delta <= 4) onSelect(); // 화면을 돌리려고 끈 것은 선택으로 치지 않는다
      }}
      onPointerOver={(e) => {
        e.stopPropagation();
        setHover(true);
      }}
      onPointerOut={() => setHover(false)}
    >
      <House closed={s.closed} highlight={selected ? "selected" : hover ? "hover" : null} />

      <mesh position-y={SOIL_TOP / 2} castShadow receiveShadow>
        <boxGeometry args={[BED_W, SOIL_TOP, BED_D]} />
        <meshStandardMaterial color={soilColor} roughness={1} />
        {selected && <Edges color="#ff6600" lineWidth={3} />}
      </mesh>

      {ps &&
        SPOTS.map(([x, z], k) => (
          <Plant key={k} position={[x, SOIL_TOP, z]} seed={k} plant={ps} species={s.species} leafy={leafy} />
        ))}

      {ps?.alive && ps.pests && <Pests spraying={s.closed} />}
      {/* 수확 연출: 작물이 솟아오른다 (동작 줄이기면 금액 표시만) */}
      {!still && bursts.map((b) => <HarvestBurst key={b.id} species={b.crop} />)}

      <Devices devices={s.devices} onHover={(key) => onHoverDevice?.(key ? { zone: s.index, key } : null)} />
    </group>
  );
}
