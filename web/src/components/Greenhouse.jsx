import { lazy, Suspense } from "react";

// three.js는 크기가 커서 3D 화면이 처음 필요할 때 따로 받는다
const Greenhouse3D = lazy(() => import("./three/Greenhouse3D.jsx"));

export default function Greenhouse(props) {
  return (
    <Suspense fallback={<div className="grid h-full place-items-center bg-dark text-sm text-dark-text">온실 화면을 불러오는 중…</div>}>
      <Greenhouse3D {...props} />
    </Suspense>
  );
}
