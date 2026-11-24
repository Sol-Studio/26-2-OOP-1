import { useMemo } from "react";
import * as THREE from "three";

// 구역 하나가 쓰는 온실 한 동의 크기 (m)
export const GH = { w: 5.6, d: 4.6, wall: 2.5, ridge: 3.5 };

// 유리·차광막은 마우스가 지나가게 (안쪽 장치에 마우스를 올리면 설명이 뜨도록)
const noHit = () => null;

const FRAME = { selected: "#ff6600", hover: "#ffffff", none: "#d5dae0" };

/** 유리 온실 한 동: 바닥, 유리 벽·박공·지붕, 뼈대.
 *  격리(closed) 중이면 유리가 붉어지고 지붕 아래 차광막이 쳐진다 (모델에서도 햇빛이 30%로 줄어든다). */
export default function House({ closed, highlight }) {
  const { w, d, wall, ridge } = GH;
  const slope = Math.hypot(d / 2, ridge - wall);
  const pitch = Math.atan2(ridge - wall, d / 2);
  const gable = useMemo(() => {
    const s = new THREE.Shape();
    s.moveTo(-d / 2, 0);
    s.lineTo(d / 2, 0);
    s.lineTo(0, ridge - wall);
    s.closePath();
    return new THREE.ShapeGeometry(s);
  }, [d, ridge, wall]);
  const frame = FRAME[highlight ?? "none"];

  const glass = (
    <meshStandardMaterial
      color={closed ? "#ff8a84" : "#e3f4ff"}
      transparent
      opacity={closed ? 0.22 : 0.1}
      roughness={0.05}
      depthWrite={false}
      side={THREE.DoubleSide}
    />
  );
  const metal = <meshStandardMaterial color={frame} metalness={highlight ? 0.1 : 0.6} roughness={0.35} />;

  return (
    <group>
      <mesh position-y={0.01} rotation-x={-Math.PI / 2} receiveShadow>
        <planeGeometry args={[w, d]} />
        <meshStandardMaterial color="#c6c9cd" roughness={0.9} />
      </mesh>

      {/* 유리: 앞뒤 벽, 양옆 벽과 박공, 지붕 두 면 */}
      {[1, -1].map((side) => (
        <group key={side}>
          <mesh position={[0, wall / 2, (side * d) / 2]} raycast={noHit}>
            <boxGeometry args={[w, wall, 0.02]} />
            {glass}
          </mesh>
          <mesh position={[(side * w) / 2, wall / 2, 0]} raycast={noHit}>
            <boxGeometry args={[0.02, wall, d]} />
            {glass}
          </mesh>
          <mesh geometry={gable} position={[(side * w) / 2, wall, 0]} rotation-y={Math.PI / 2} raycast={noHit}>
            {glass}
          </mesh>
          <mesh position={[0, (wall + ridge) / 2, (side * d) / 4]} rotation-x={side * pitch} raycast={noHit}>
            <boxGeometry args={[w, 0.02, slope]} />
            {glass}
          </mesh>
          {closed && (
            <mesh position={[0, (wall + ridge) / 2 - 0.12, (side * d) / 4]} rotation-x={side * pitch} castShadow raycast={noHit}>
              <boxGeometry args={[w - 0.1, 0.01, slope - 0.1]} />
              <meshStandardMaterial color="#3d4148" transparent opacity={0.8} side={THREE.DoubleSide} />
            </mesh>
          )}
        </group>
      ))}

      {/* 뼈대: 기둥, 서까래, 용마루, 처마 */}
      {[-w / 2, 0, w / 2].map((x) => (
        <group key={x} position-x={x}>
          {[1, -1].map((side) => (
            <group key={side}>
              <mesh position={[0, wall / 2, (side * d) / 2]} castShadow>
                <boxGeometry args={[0.07, wall, 0.07]} />
                {metal}
              </mesh>
              <mesh position={[0, (wall + ridge) / 2, (side * d) / 4]} rotation-x={side * pitch} castShadow>
                <boxGeometry args={[0.07, 0.07, slope]} />
                {metal}
              </mesh>
            </group>
          ))}
        </group>
      ))}
      <mesh position={[0, ridge, 0]}>
        <boxGeometry args={[w, 0.09, 0.09]} />
        {metal}
      </mesh>
      {[1, -1].map((side) => (
        <mesh key={side} position={[0, wall, (side * d) / 2]}>
          <boxGeometry args={[w, 0.07, 0.07]} />
          {metal}
        </mesh>
      ))}
    </group>
  );
}
