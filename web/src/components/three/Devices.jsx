import { useEffect, useMemo, useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { useReducedMotion } from "../../lib/motion.js";
import { GH } from "./House.jsx";

export const BED_W = 3.2;
export const BED_D = 2.4;
export const SOIL_TOP = 0.4;

const OFF = "#8a9099";
export const rand = (n) => {
  const x = Math.sin(n * 12.9898) * 43758.5453;
  return x - Math.floor(x);
};

/** 급수·비료는 한 단계(10분)에만 투입량이 있어서 그대로 그리면 깜빡이고 끝난다.
 *  눈에 보이도록 마지막으로 켜진 뒤 ms 동안은 켜진 것으로 본다. */
function useHold(on, ms = 1600) {
  const [held, setHeld] = useState(on);
  useEffect(() => {
    if (on) {
      setHeld(true);
      return;
    }
    const t = setTimeout(() => setHeld(false), ms);
    return () => clearTimeout(t);
  }, [on, ms]);
  return on || held;
}

/** 작은 입자 묶음. place(p, obj)가 입자 p(t: 0~1 진행도, a·b·c: 입자마다 고정 난수)의 위치·크기를 정한다. */
export function Particles({ on: wanted, count, size, color, opacity = 1, speed = 1, emissive, place }) {
  const still = useReducedMotion(); // 훅은 조건 없이 늘 불러야 한다
  const on = wanted && !still;
  const ref = useRef(null);
  const dummy = useMemo(() => new THREE.Object3D(), []);
  const parts = useMemo(
    () => Array.from({ length: count }, (_, k) => ({ t: k / count, a: rand(k * 3 + 1), b: rand(k * 3 + 2), c: rand(k * 3 + 3) })),
    [count],
  );
  useFrame((_, dt) => {
    const m = ref.current;
    if (!m) return;
    m.visible = on;
    if (!on) return;
    parts.forEach((p, k) => {
      p.t = (p.t + dt * speed) % 1;
      dummy.scale.setScalar(1);
      place(p, dummy);
      dummy.updateMatrix();
      m.setMatrixAt(k, dummy.matrix);
    });
    m.instanceMatrix.needsUpdate = true;
  });
  return (
    <instancedMesh ref={ref} args={[undefined, undefined, count]} visible={false} frustumCulled={false} raycast={() => null}>
      <sphereGeometry args={[size, 6, 6]} />
      <meshStandardMaterial
        color={color}
        emissive={emissive ?? "#000000"}
        emissiveIntensity={emissive ? 0.6 : 0}
        transparent={opacity < 1}
        opacity={opacity}
        depthWrite={opacity >= 1}
      />
    </instancedMesh>
  );
}

/** 구역 하나의 장치 8개. 꺼져 있어도 자리에 보이고, 켜지면 움직이거나 빛난다.
 *  onHover(장치 키 | null): 마우스가 장치에 올라가거나 벗어날 때 (설명 표시용) */
export default function Devices({ devices: d, onHover }) {
  const water = useHold(d.water);
  const fertilizer = useHold(d.fertilizer);
  // 장치 묶음에 붙이는 마우스 처리. 구역 선택·강조도 같이 되도록 이벤트를 막지 않는다.
  const h = (key) => ({ onPointerOver: () => onHover?.(key), onPointerOut: () => onHover?.(null) });
  return (
    <>
      <Heater on={d.heater} h={h("heater")} />
      <Cooler on={d.cooler} h={h("cooler")} />
      <Fan on={d.fan} h={h("fan")} />
      <Humidifier on={d.humidifier} h={h("humidifier")} />
      <Dehumidifier on={d.dehumidifier} h={h("dehumidifier")} />
      <GrowLight level={d.light} h={h("light")} />
      <Irrigation on={water} h={h("irrigation")} />
      <Fertilizer on={fertilizer} h={h("fertilizer")} />
    </>
  );
}

/** 난방기: 왼쪽 벽의 방열기. 켜지면 방열판이 달아오르고 더운 공기가 올라간다. */
function Heater({ on, h }) {
  return (
    <group position={[-GH.w / 2 + 0.2, 0, -0.5]} {...h}>
      <mesh position-y={0.5} castShadow>
        <boxGeometry args={[0.22, 0.8, 1.0]} />
        <meshStandardMaterial color="#e3e6ea" />
      </mesh>
      {[-0.36, -0.18, 0, 0.18, 0.36].map((z) => (
        <mesh key={z} position={[0.13, 0.5, z]}>
          <boxGeometry args={[0.04, 0.62, 0.07]} />
          <meshStandardMaterial color={on ? "#ff5a1f" : OFF} emissive="#ff4a10" emissiveIntensity={on ? 2.2 : 0} />
        </mesh>
      ))}
      <Particles
        on={on}
        count={14}
        size={0.05}
        color="#ffb37a"
        opacity={0.45}
        speed={0.6}
        place={(p, o) => {
          o.position.set(0.25 + p.a * 0.35, 0.9 + p.t * 1.2, (p.b - 0.5) * 0.9);
          o.scale.setScalar(1 - p.t * 0.7);
        }}
      />
    </group>
  );
}

/** 냉방기: 뒷벽 위쪽의 에어컨. 켜지면 바람 구멍이 파랗게 빛나고 찬 공기가 내려온다. */
function Cooler({ on, h }) {
  return (
    <group position={[0.9, 2.0, -GH.d / 2 + 0.18]} {...h}>
      <mesh castShadow>
        <boxGeometry args={[1.2, 0.36, 0.26]} />
        <meshStandardMaterial color="#f4f6f8" />
      </mesh>
      <mesh position={[0, -0.14, 0.135]}>
        <boxGeometry args={[1.0, 0.05, 0.02]} />
        <meshStandardMaterial color={on ? "#5ec8ff" : OFF} emissive="#3fb6ff" emissiveIntensity={on ? 2 : 0} />
      </mesh>
      <mesh position={[0.48, 0.08, 0.135]}>
        <circleGeometry args={[0.025, 10]} />
        <meshStandardMaterial color={on ? "#3fb6ff" : "#555a61"} emissive="#3fb6ff" emissiveIntensity={on ? 2 : 0} />
      </mesh>
      <Particles
        on={on}
        count={18}
        size={0.045}
        color="#c9eeff"
        opacity={0.55}
        speed={0.7}
        place={(p, o) => o.position.set((p.a - 0.5) * 1.0, -0.2 - p.t * 1.1, 0.15 + p.t * (0.6 + p.b * 0.6))}
      />
    </group>
  );
}

/** 환기팬: 오른쪽 벽. 켜지면 날개가 돈다. */
function Fan({ on, h }) {
  const blades = useRef(null);
  const still = useReducedMotion();
  useFrame((_, dt) => {
    if (on && !still && blades.current) blades.current.rotation.z += dt * 14;
  });
  return (
    <group position={[GH.w / 2 - 0.08, 1.5, 0.9]} rotation-y={-Math.PI / 2} {...h}>
      <mesh>
        <boxGeometry args={[0.9, 0.9, 0.1]} />
        <meshStandardMaterial color="#b7bdc5" metalness={0.4} roughness={0.5} transparent opacity={0.35} />
      </mesh>
      <mesh position-z={0.06}>
        <torusGeometry args={[0.38, 0.035, 8, 28]} />
        <meshStandardMaterial color="#9aa1aa" metalness={0.5} roughness={0.4} />
      </mesh>
      <group ref={blades} position-z={0.08}>
        {[0, 1, 2, 3].map((k) => (
          <group key={k} rotation-z={(k * Math.PI) / 2}>
            <mesh position-y={0.17} rotation-y={0.35}>
              <boxGeometry args={[0.11, 0.3, 0.015]} />
              <meshStandardMaterial color={on ? "#ff6600" : "#c3c8ce"} />
            </mesh>
          </group>
        ))}
        <mesh rotation-x={Math.PI / 2}>
          <cylinderGeometry args={[0.06, 0.06, 0.06, 12]} />
          <meshStandardMaterial color="#5c636c" />
        </mesh>
      </group>
    </group>
  );
}

/** 가습기: 앞쪽 왼편 바닥. 켜지면 안개가 피어오른다. */
function Humidifier({ on, h }) {
  return (
    <group position={[-GH.w / 2 + 0.7, 0, GH.d / 2 - 0.6]} {...h}>
      <mesh position-y={0.3} castShadow>
        <cylinderGeometry args={[0.2, 0.24, 0.6, 20]} />
        <meshStandardMaterial color="#f5f7f9" />
      </mesh>
      <mesh position-y={0.64}>
        <cylinderGeometry args={[0.06, 0.08, 0.1, 12]} />
        <meshStandardMaterial color="#9aa1aa" />
      </mesh>
      <mesh position={[0, 0.35, 0.235]}>
        <circleGeometry args={[0.03, 10]} />
        <meshStandardMaterial color={on ? "#5ec8ff" : "#555a61"} emissive="#3fb6ff" emissiveIntensity={on ? 2 : 0} />
      </mesh>
      <Particles
        on={on}
        count={20}
        size={0.07}
        color="#ffffff"
        opacity={0.35}
        speed={0.45}
        place={(p, o) => {
          o.position.set((p.a - 0.5) * 0.5 * p.t + 0.25 * p.t, 0.7 + p.t * 1.0, (p.b - 0.5) * 0.5 * p.t - 0.2 * p.t);
          o.scale.setScalar(0.6 + p.t * 1.6);
        }}
      />
    </group>
  );
}

/** 제습기: 앞쪽 오른편 바닥. 켜지면 위 팬이 돌고 주변 습기를 빨아들인다. */
function Dehumidifier({ on, h }) {
  const fan = useRef(null);
  const still = useReducedMotion();
  useFrame((_, dt) => {
    if (on && !still && fan.current) fan.current.rotation.y += dt * 10;
  });
  return (
    <group position={[GH.w / 2 - 0.7, 0, GH.d / 2 - 0.6]} {...h}>
      <mesh position-y={0.35} castShadow>
        <boxGeometry args={[0.5, 0.7, 0.38]} />
        <meshStandardMaterial color="#aeb5bd" />
      </mesh>
      <mesh position={[0, 0.25, 0.195]}>
        <boxGeometry args={[0.32, 0.18, 0.01]} />
        <meshStandardMaterial color="#6fb7e8" transparent opacity={0.7} />
      </mesh>
      <mesh position={[0.17, 0.6, 0.195]}>
        <circleGeometry args={[0.025, 10]} />
        <meshStandardMaterial color={on ? "#2ee08a" : "#555a61"} emissive="#20d080" emissiveIntensity={on ? 2 : 0} />
      </mesh>
      <group ref={fan} position-y={0.71}>
        {[0, 1, 2].map((k) => (
          <mesh key={k} rotation-y={(k * Math.PI * 2) / 3}>
            <boxGeometry args={[0.3, 0.015, 0.06]} />
            <meshStandardMaterial color={on ? "#ff6600" : "#7b828b"} />
          </mesh>
        ))}
      </group>
      <Particles
        on={on}
        count={16}
        size={0.035}
        color="#9fd6ff"
        opacity={0.6}
        speed={0.8}
        place={(p, o) => {
          const r = 0.9 * (1 - p.t);
          const a = p.a * Math.PI * 2;
          o.position.set(Math.cos(a) * r, 0.75 + (p.b * 0.8 + 0.1) * (1 - p.t), Math.sin(a) * r);
        }}
      />
    </group>
  );
}

/** 인공조명: 작물 위에 매단 LED 등. 밝기(0~1)만큼 빛나고 빛 기둥이 내려온다.
 *  조명이 켜지고 꺼질 때 셰이더를 다시 만들지 않도록 빛은 늘 두고 세기만 바꾼다. */
function GrowLight({ level, h }) {
  const y = 2.15;
  return (
    <group position-y={y} {...h}>
      {[-1.2, 1.2].map((x) => (
        <mesh key={x} position={[x, (GH.wall + 0.3 - y) / 2 + 0.03, 0]}>
          <cylinderGeometry args={[0.008, 0.008, GH.wall + 0.3 - y, 4]} />
          <meshStandardMaterial color="#555a61" />
        </mesh>
      ))}
      <mesh>
        <boxGeometry args={[BED_W * 0.85, 0.06, 0.22]} />
        <meshStandardMaterial color="#3a3f47" emissive="#ffe0f0" emissiveIntensity={level * 3} />
      </mesh>
      <mesh position-y={-(y - SOIL_TOP) / 2} visible={level > 0} raycast={() => null}>
        <boxGeometry args={[BED_W * 0.85, y - SOIL_TOP - 0.05, BED_D * 0.8]} />
        <meshBasicMaterial color="#ffd6ec" transparent opacity={level * 0.1} depthWrite={false} />
      </mesh>
      <pointLight position-y={-0.3} intensity={level * 6} distance={4} decay={2} color="#ffd9ea" />
    </group>
  );
}

/** 급수: 뒤쪽 왼편 물탱크와 점적 배관. 물을 줄 때 배관이 파래지고 물방울이 떨어진다. */
function Irrigation({ on, h }) {
  const pipeY = SOIL_TOP + 0.08;
  const tankX = -GH.w / 2 + 0.65;
  const pipeLen = BED_W / 2 - tankX;
  return (
    <group {...h}>
      <group position={[tankX, 0, -GH.d / 2 + 0.55]}>
        <mesh position-y={0.45} castShadow>
          <cylinderGeometry args={[0.3, 0.3, 0.9, 20]} />
          <meshStandardMaterial color="#5ea9de" transparent opacity={0.85} />
        </mesh>
        <mesh position-y={0.93}>
          <cylinderGeometry args={[0.31, 0.31, 0.06, 20]} />
          <meshStandardMaterial color="#2f6f9e" />
        </mesh>
      </group>
      {[
        [[(tankX + BED_W / 2) / 2, pipeY, -BED_D / 2 + 0.12], [0, 0, Math.PI / 2], pipeLen],
        [[tankX, pipeY, (-GH.d / 2 + 0.55 - BED_D / 2 + 0.12) / 2], [Math.PI / 2, 0, 0], GH.d / 2 - 0.55 - BED_D / 2 + 0.12],
      ].map(([pos, rot, len], k) => (
        <mesh key={k} position={pos} rotation={rot}>
          <cylinderGeometry args={[0.025, 0.025, len, 8]} />
          <meshStandardMaterial color={on ? "#2a8fe0" : OFF} emissive="#1f7fd0" emissiveIntensity={on ? 0.8 : 0} />
        </mesh>
      ))}
      <Particles
        on={on}
        count={28}
        size={0.03}
        color="#4aa3df"
        emissive="#2a7fbf"
        speed={1.4}
        place={(p, o) => o.position.set((p.a - 0.5) * BED_W * 0.9, 1.3 - p.t * (1.3 - SOIL_TOP), (p.b - 0.5) * BED_D * 0.9)}
      />
    </group>
  );
}

/** 비료(양액): 뒤쪽 오른편 양액 탱크. 비료를 줄 때 탱크가 초록빛으로 빛나고 알갱이가 흩뿌려진다. */
function Fertilizer({ on, h }) {
  return (
    <group {...h}>
      <group position={[GH.w / 2 - 0.65, 0, -GH.d / 2 + 0.55]}>
        <mesh position-y={0.4} castShadow>
          <cylinderGeometry args={[0.24, 0.24, 0.8, 20]} />
          <meshStandardMaterial color="#e9f2dc" transparent opacity={0.55} />
        </mesh>
        <mesh position-y={0.3}>
          <cylinderGeometry args={[0.21, 0.21, 0.55, 20]} />
          <meshStandardMaterial color="#7cc243" emissive="#5fae2a" emissiveIntensity={on ? 1.4 : 0} />
        </mesh>
        <mesh position-y={0.83}>
          <cylinderGeometry args={[0.25, 0.25, 0.06, 20]} />
          <meshStandardMaterial color="#3f7d22" />
        </mesh>
      </group>
      <Particles
        on={on}
        count={30}
        size={0.022}
        color="#86d14e"
        emissive="#5fae2a"
        speed={1.1}
        place={(p, o) => o.position.set((p.a - 0.5) * BED_W * 0.9, 1.0 - p.t * (1.0 - SOIL_TOP), (p.c - 0.5) * BED_D * 0.9)}
      />
    </group>
  );
}
