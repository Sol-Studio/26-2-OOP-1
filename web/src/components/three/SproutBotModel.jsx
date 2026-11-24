import { useEffect, useMemo } from "react";
import * as THREE from "three";

/** 새싹봇 몸 모델 (발바닥이 원점, 키 약 1.15). 움직일 부분을 parts.current에 넣어 준다:
 *  body(몸통), sprout(새싹), armL·armR, legL·legR, eyes(눈 재질 2개 — 색을 바꿀 수 있다) */
export default function SproutBotModel({ parts }) {
  const eyeMats = useMemo(() => [0, 1].map(() => new THREE.MeshBasicMaterial({ color: "#5fe0a8" })), []);
  useEffect(() => {
    parts.current.eyes = eyeMats;
    return () => eyeMats.forEach((m) => m.dispose());
  }, [eyeMats, parts]);
  const set = (name) => (el) => (parts.current[name] = el);
  const white = <meshStandardMaterial color="#f6f7f9" roughness={0.35} metalness={0.05} />;

  return (
    <>
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
    </>
  );
}
