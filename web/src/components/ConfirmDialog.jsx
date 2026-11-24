import { useEffect, useRef } from "react";
import { useFarm } from "../lib/farm.jsx";

export default function ConfirmDialog() {
  const { confirm, setConfirm } = useFarm();
  const ref = useRef(null);

  useEffect(() => {
    const dlg = ref.current;
    if (confirm && !dlg.open) dlg.showModal();
    if (!confirm && dlg.open) dlg.close();
  }, [confirm]);

  const ok = () => {
    confirm?.action();
    setConfirm(null);
  };

  return (
    <dialog
      ref={ref}
      onClose={() => setConfirm(null)}
      className="m-auto w-[min(92vw,380px)] rounded-2xl bg-card p-6 text-ink shadow-xl backdrop:bg-black/40"
    >
      <h2 className="text-base font-bold">{confirm?.title}</h2>
      <p className="mt-2 text-sm text-muted">{confirm?.message}</p>
      <div className="mt-6 flex justify-end gap-2">
        <button onClick={() => setConfirm(null)} className="rounded-lg px-4 py-2 text-sm font-medium ring-1 ring-line hover:bg-pressed">
          취소
        </button>
        <button onClick={ok} className="rounded-lg bg-critical px-4 py-2 text-sm font-bold text-white hover:brightness-95">
          {confirm?.confirmLabel ?? "확인"}
        </button>
      </div>
    </dialog>
  );
}
