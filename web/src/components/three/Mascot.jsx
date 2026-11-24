import { useEffect, useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { useReducedMotion } from "../../lib/motion.js";
import { GH } from "./House.jsx";
import { zonePosition } from "./Zone.jsx";

/* 에버그로우 마스코트 '새싹봇': 머리에 새싹이 난 동그란 흰 로봇 (이 프로젝트용으로 새로 만든 캐릭터).
 * 평소엔 온실 사이 통로를 순찰하고, 병충해가 생기면 그 온실 앞으로 달려가 뛰면서 알린다. */

// 통로 격자: 온실 사이·바깥쪽 길. 세로로는 온실 사이 통로(AISLE_X)로만 다닐 수 있다 (온실을 뚫고 가지 않게).
const COL = GH.w + 1.2; // 온실 열 간격 (zonePosition과 같다)
const ROW = GH.d + 1.4;
const AISLE_X = [-1.5 * COL - 0.4, -COL / 2, COL / 2, 1.5 * COL + 0.4];
const XS = [...new Set([...AISLE_X, -COL, 0, COL])].sort((a, b) => a - b); // 온실 앞자리 x도 마디로
const ZS = [-ROW, 0, ROW]; // 뒤쪽 바깥 길, 두 줄 사이 길, 앞쪽 바깥 길
const key = (i, j) => `${i},${j}`;

function neighbors(i, j) {
  const out = [];
  if (i > 0) out.push([i - 1, j]);
  if (i < XS.length - 1) out.push([i + 1, j]);
  if (AISLE_X.includes(XS[i])) {
    if (j > 0) out.push([i, j - 1]);
    if (j < ZS.length - 1) out.push([i, j + 1]);
  }
  return out;
}

/** 격자 위 최단 길 (너비 우선 탐색). [[i, j], …] 시작점은 빼고 돌려준다. */
function findPath(from, to) {
  const prev = new Map([[key(...from), null]]);
  const queue = [from];
  while (queue.length) {
    const cur = queue.shift();
    if (cur[0] === to[0] && cur[1] === to[1]) break;
    for (const n of neighbors(...cur)) {
      if (!prev.has(key(...n))) {
        prev.set(key(...n), cur);
        queue.push(n);
      }
    }
  }
  const path = [];
  for (let c = to; c && key(...c) !== key(...from); c = prev.get(key(...c))) path.unshift(c);
  return path;
}

/** 구역 i 온실 앞 통로 마디: 앞줄 온실은 바깥 길, 뒷줄 온실은 두 줄 사이 길 */
function doorNode(i) {
  const [x, , z] = zonePosition(i);
  return [XS.indexOf(x), z < 0 ? 1 : 2];
}

const nodePos = ([i, j]) => new THREE.Vector3(XS[i], 0, ZS[j]);
const START = [2, 1]; // 처음 자리: 왼쪽 통로와 두 줄 사이 길이 만나는 곳
// 고정 배열로 둔다 (렌더마다 새 배열을 넘기면 화면이 갱신될 때마다 처음 자리로 순간이동한다)
const START_POS = nodePos(START).toArray();
const SIZE = 1.7; // 전체 보기에서도 눈에 띄게 (온실 벽 높이 2.5m의 절반쯤)

/**
 * pestZones: 병충해가 있는 구역 번호들. bubble: 말풍선 DOM ref (위치를 매 프레임 옮긴다).
 * onMessage(글|null, 구역|null): 할 말이 바뀔 때. onPick(구역): 새싹봇을 누르면.
 */
export default function Mascot({ pestZones, bubble, onMessage, onPick }) {
  const root = useRef(null);
  const parts = useRef({});
  const still = useReducedMotion();
  const st = useRef({ node: START, path: [], alert: null, arrived: false, heading: 0, phase: 0, cheerUntil: 0 });
  const tmp = useMemo(() => ({ v: new THREE.Vector3(), head: new THREE.Vector3() }), []);
  const target = pestZones[0] ?? null;

  // 알릴 구역이 바뀌면 그쪽으로 길을 다시 찾는다. 병충해가 끝나면 한마디 하고 순찰로 돌아간다.
  useEffect(() => {
    const s = st.current;
    if (target == null) {
      if (s.alert != null) {
        onMessage("방제 완료! 다시 순찰할게요", null);
        s.cheerUntil = performance.now() + 3000;
      }
      s.alert = null;
      s.arrived = false;
      s.path = [];
      return;
    }
    if (s.alert === target) return;
    s.alert = target;
    s.arrived = false;
    s.path = findPath(s.node, doorNode(target));
    if (still) {
      s.node = doorNode(target); // 동작 줄이기: 걷지 않고 바로 그 자리에
      s.path = [];
      s.arrived = true;
      root.current?.position.copy(nodePos(s.node));
    }
    onMessage("큰일이에요! 병충해가 생겼어요", target);
  }, [target, still, onMessage]);

  useFrame(({ camera, size }, dt) => {
    const s = st.current;
    const g = root.current;
    if (!g) return;
    dt = Math.min(dt, 0.1);
    const p = parts.current;
    if (s.cheerUntil && performance.now() > s.cheerUntil) {
      s.cheerUntil = 0;
      onMessage(null, null);
    }

    // 다음에 갈 마디 정하기: 순찰이면 아무 이웃으로, 알리는 중이면 찾아 둔 길대로
    if (!s.path.length && !s.arrived && !still) {
      if (s.alert != null) {
        s.arrived = true;
        onMessage("여기예요! 이 온실에 병충해가 있어요", s.alert);
      } else {
        const options = neighbors(...s.node);
        s.path = [options[Math.floor(Math.random() * options.length)]];
      }
    }

    let moving = false;
    if (s.path.length && !still) {
      const goal = nodePos(s.path[0]);
      tmp.v.subVectors(goal, g.position);
      const dist = tmp.v.length();
      const speed = s.alert != null ? 4.2 : 1.1; // 알릴 땐 달린다
      if (dist < 0.05) {
        s.node = s.path.shift();
      } else {
        g.position.addScaledVector(tmp.v.normalize(), Math.min(dist, speed * dt));
        const want = Math.atan2(tmp.v.x, tmp.v.z);
        s.heading += Math.atan2(Math.sin(want - s.heading), Math.cos(want - s.heading)) * Math.min(1, dt * 10);
        moving = true;
      }
    } else if (s.arrived && s.alert != null) {
      // 도착: 온실 쪽을 바라본다
      const [zx, , zz] = zonePosition(s.alert);
      const want = Math.atan2(zx - g.position.x, zz - g.position.z);
      s.heading += Math.atan2(Math.sin(want - s.heading), Math.cos(want - s.heading)) * Math.min(1, dt * 6);
    }
    g.rotation.y = s.heading;

    // 몸짓: 걸을 땐 다리·팔을 흔들고, 알릴 땐 펄쩍펄쩍 뛰며 두 팔을 흔든다
    const fast = s.alert != null;
    if (!still) s.phase += dt * (moving ? (fast ? 18 : 8) : 4);
    const swing = moving ? Math.sin(s.phase) * (fast ? 0.9 : 0.5) : 0;
    const alarm = s.arrived && s.alert != null;
    const hop = alarm && !still ? Math.abs(Math.sin(s.phase * 1.6)) * 0.35 : moving ? Math.abs(Math.sin(s.phase)) * 0.05 : 0;
    p.body && (p.body.position.y = 0.62 + hop);
    p.legL && (p.legL.rotation.x = swing);
    p.legR && (p.legR.rotation.x = -swing);
    if (p.armL && p.armR) {
      if (alarm) {
        p.armL.rotation.z = 2.4 + Math.sin(s.phase * 3) * 0.4;
        p.armR.rotation.z = -2.4 - Math.sin(s.phase * 3) * 0.4;
        p.armL.rotation.x = p.armR.rotation.x = 0;
      } else {
        p.armL.rotation.z = 0.25;
        p.armR.rotation.z = -0.25;
        p.armL.rotation.x = -swing;
        p.armR.rotation.x = swing;
      }
    }
    p.sprout && (p.sprout.rotation.z = Math.sin(s.phase * 0.7) * 0.25);
    if (p.eyes) p.eyes.forEach((m) => (m.color.set(alarm ? "#ff5a4f" : "#5fe0a8")));

    // 말풍선을 머리 위에 붙인다
    const el = bubble.current;
    if (el) {
      tmp.head.set(g.position.x, (1.15 + hop) * SIZE, g.position.z).project(camera);
      const x = ((tmp.head.x + 1) / 2) * size.width;
      const y = ((1 - tmp.head.y) / 2) * size.height;
      el.style.transform = `translate(${x}px, ${y}px) translate(-50%, -100%)`;
      el.style.visibility = tmp.head.z > 1 ? "hidden" : "visible";
    }
  });

  const eyeMats = useMemo(() => [0, 1].map(() => new THREE.MeshBasicMaterial({ color: "#5fe0a8" })), []);
  useEffect(() => {
    parts.current.eyes = eyeMats;
  }, [eyeMats]);
  const set = (name) => (el) => (parts.current[name] = el);
  const white = <meshStandardMaterial color="#f6f7f9" roughness={0.35} metalness={0.05} />;

  return (
    <group
      ref={root}
      position={START_POS}
      scale={SIZE}
      onClick={(e) => {
        e.stopPropagation();
        if (st.current.alert != null) onPick(st.current.alert);
      }}
    >
      {/* 몸통(머리 겸) */}
      <group ref={set("body")} position-y={0.62}>
        <mesh castShadow scale={[0.36, 0.33, 0.34]}>
          <sphereGeometry args={[1, 32, 24]} />
          {white}
        </mesh>
        {/* 배의 주황 띠 (에버그로우 색) */}
        <mesh position-y={-0.1} rotation-x={Math.PI / 2} scale={[1, 1, 0.6]}>
          <torusGeometry args={[0.335, 0.035, 10, 40]} />
          <meshStandardMaterial color="#ff6600" />
        </mesh>
        {/* 얼굴 화면과 눈 */}
        <mesh position={[0, 0.05, 0.26]} scale={[0.22, 0.14, 0.1]}>
          <sphereGeometry args={[1, 24, 16]} />
          <meshStandardMaterial color="#1d242c" roughness={0.2} metalness={0.4} />
        </mesh>
        {[-0.08, 0.08].map((x, k) => (
          <mesh key={x} position={[x, 0.07, 0.355]} material={eyeMats[k]}>
            <capsuleGeometry args={[0.025, 0.03, 4, 8]} />
          </mesh>
        ))}
        {/* 머리 위 새싹 */}
        <group ref={set("sprout")} position-y={0.32}>
          <mesh position-y={0.08}>
            <cylinderGeometry args={[0.015, 0.02, 0.16, 8]} />
            <meshStandardMaterial color="#3f9b4c" />
          </mesh>
          {[1, -1].map((side) => (
            <mesh key={side} position={[side * 0.07, 0.17, 0]} rotation-z={side * -0.6} scale={[0.09, 0.03, 0.05]}>
              <sphereGeometry args={[1, 16, 10]} />
              <meshStandardMaterial color="#5cc463" />
            </mesh>
          ))}
        </group>
        {/* 팔 */}
        {[
          ["armL", 1],
          ["armR", -1],
        ].map(([name, side]) => (
          <group key={name} ref={set(name)} position={[side * 0.34, 0, 0]} rotation-z={side * 0.25}>
            <mesh position-y={-0.12} castShadow>
              <capsuleGeometry args={[0.045, 0.14, 4, 10]} />
              {white}
            </mesh>
          </group>
        ))}
      </group>
      {/* 다리 */}
      {[
        ["legL", 0.13],
        ["legR", -0.13],
      ].map(([name, x]) => (
        <group key={name} ref={set(name)} position={[x, 0.32, 0]}>
          <mesh position-y={-0.14} castShadow>
            <cylinderGeometry args={[0.05, 0.05, 0.26, 10]} />
            <meshStandardMaterial color="#c9ced4" />
          </mesh>
          <mesh position={[0, -0.28, 0.04]} scale={[0.08, 0.04, 0.11]} castShadow>
            <sphereGeometry args={[1, 12, 8]} />
            <meshStandardMaterial color="#ff6600" />
          </mesh>
        </group>
      ))}
    </group>
  );
}
