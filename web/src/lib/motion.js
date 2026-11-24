import { useEffect, useState } from "react";

const QUERY = "(prefers-reduced-motion: reduce)";

/** 운영체제에서 '동작 줄이기'를 켰는지. 켰으면 입자·회전·카메라 비행 같은 움직임을 끈다. */
export function useReducedMotion() {
  const [reduced, setReduced] = useState(() => matchMedia(QUERY).matches);
  useEffect(() => {
    const mq = matchMedia(QUERY);
    const on = () => setReduced(mq.matches);
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);
  return reduced;
}
