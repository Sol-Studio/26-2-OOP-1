import { useMemo } from "react";
import * as THREE from "three";

// 포기가 70여 개라 도형은 하나씩만 만들어 같이 쓴다
const SPHERE = new THREE.SphereGeometry(1, 12, 8);
const STEM = new THREE.CylinderGeometry(1, 1, 1, 6);

const GREEN = new THREE.Color("#2f7d4a");
const YELLOW = new THREE.Color("#c8b64a");
const DEAD = new THREE.Color("#8b7d5a");
const UNRIPE = "#9bc47a";
const FRUIT_COLOR = { 토마토: "#d63a2f", 딸기: "#e0405a", 파프리카: "#e8a91c", 오이: "#4f9a3a" };

/** 포기 하나. 생장도만큼 자라고, 건강이 나쁘면 누렇게, 죽으면 쓰러진다.
 *  잎채소는 바닥에 퍼지는 로제트, 열매채소는 줄기에 잎이 달리고 개화(55%) 뒤 열매가 맺힌다. */
export default function Plant({ position, seed, plant, species, leafy }) {
  const { growth, health, alive, pests } = plant;
  const g = growth / 100;
  const leaf = useMemo(
    () => (alive ? GREEN.clone().lerp(YELLOW, Math.min(1, ((100 - health) / 100) * 1.4)) : DEAD),
    [alive, health],
  );
  const vary = 0.9 + 0.1 * ((seed * 7) % 3); // 포기마다 키를 조금씩 다르게
  const turn = seed * 2.4;

  return (
    <group position={position} rotation-y={turn} rotation-z={alive ? 0 : 1.15} scale={[1, alive ? vary : 0.6, 1]}>
      {leafy ? <Rosette g={g} color={leaf} /> : <Vine g={g} color={leaf} species={species} />}
      {pests && alive && <Bugs g={g} leafy={leafy} />}
    </group>
  );
}

function Leaf({ position, scale, rotation, color }) {
  return (
    <mesh geometry={SPHERE} position={position} scale={scale} rotation={rotation} castShadow>
      <meshStandardMaterial color={color} roughness={0.8} />
    </mesh>
  );
}

function Rosette({ g, color }) {
  const n = 4 + Math.round(5 * g);
  const size = 0.06 + 0.2 * g;
  return Array.from({ length: n }, (_, i) => {
    const a = i * 2.4;
    const r = size * 0.55;
    return (
      <Leaf
        key={i}
        color={color}
        position={[Math.cos(a) * r, 0.03 + size * 0.3 * (i % 2), Math.sin(a) * r]}
        rotation={[0, -a, 0.45]}
        scale={[size, size * 0.28, size * 0.6]}
      />
    );
  });
}

function Vine({ g, color, species }) {
  const h = 0.12 + 1.0 * g;
  const levels = 2 + Math.round(3 * g);
  const leafSize = 0.07 + 0.11 * g;
  const fruit = g >= 0.55 ? (g >= 0.75 ? (FRUIT_COLOR[species] ?? "#d63a2f") : UNRIPE) : null;
  const fr = 0.045 + 0.035 * Math.max(0, (g - 0.55) / 0.45);

  return (
    <>
      <mesh geometry={STEM} position-y={h / 2} scale={[0.022, h, 0.022]} castShadow>
        <meshStandardMaterial color={color} roughness={0.9} />
      </mesh>
      {Array.from({ length: levels }, (_, j) => {
        const y = h * (0.3 + (0.65 * j) / Math.max(1, levels - 1));
        const a = j * 1.3;
        return [1, -1].map((side) => (
          <Leaf
            key={`${j}${side}`}
            color={color}
            position={[Math.cos(a) * 0.09 * side, y, Math.sin(a) * 0.09 * side]}
            rotation={[0, -a, side * 0.35]}
            scale={[leafSize, leafSize * 0.3, leafSize * 0.55]}
          />
        ));
      })}
      <Leaf color={color} position={[0, h, 0]} rotation={[0, 0, 0]} scale={[leafSize * 0.8, leafSize * 0.6, leafSize * 0.8]} />
      {fruit &&
        [0.4, 0.6].map((t, k) => (
          <mesh key={k} geometry={SPHERE} position={[k ? -0.08 : 0.09, h * t, k ? 0.05 : -0.03]} scale={fr} castShadow>
            <meshStandardMaterial color={fruit} roughness={0.45} />
          </mesh>
        ))}
    </>
  );
}

/** 병충해: 잎 위의 작은 벌레들 */
function Bugs({ g, leafy }) {
  const top = leafy ? 0.06 + 0.08 * g : 0.15 + 0.8 * g;
  return [
    [0.07, 0.5, 0.03],
    [-0.06, 0.8, -0.05],
    [0.02, 0.3, -0.08],
  ].map(([x, t, z], k) => (
    <mesh key={k} geometry={SPHERE} position={[x, top * t + 0.03, z]} scale={0.022}>
      <meshStandardMaterial color="#1e140c" />
    </mesh>
  ));
}
