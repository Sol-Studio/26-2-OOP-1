import { useEffect, useLayoutEffect, useMemo, useRef } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";
import { feature } from "topojson-client";
import land110 from "world-atlas/land-110m.json";
import { useReducedMotion } from "../../lib/motion.js";

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
export default function LoginGlobe({ dive = false, onDived }) {
  return (
    <Canvas dpr={[1, 2]} camera={{ position: [0, 0, 4.3], fov: 40 }} gl={{ antialias: true, alpha: true }}>
      <ambientLight intensity={0.6} />
      <directionalLight position={[-3, 2, 4]} intensity={1.4} />
      <Globe dive={dive} onDived={onDived} />
    </Canvas>
  );
}

function Globe({ dive, onDived }) {
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
    } else if (!still && spin.current) spin.current.rotation.y += dt * 0.12;
    if (ring.current) {
      const t = still ? 0.5 : (clock.elapsedTime * 0.6) % 1;
      ring.current.scale.setScalar(1 + t * 2.5);
      ring.current.material.opacity = 0.9 * (1 - t);
    }
  });

  return (
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
