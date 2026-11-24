// chart.js 공통 설정. 필요한 부품만 등록해서 묶음 크기를 줄인다.
import {
  BarController,
  BarElement,
  CategoryScale,
  Chart,
  Filler,
  LinearScale,
  LineController,
  LineElement,
  PointElement,
  Tooltip,
} from "chart.js";

Chart.register(BarController, BarElement, LineController, LineElement, PointElement, CategoryScale, LinearScale, Tooltip, Filler);
Chart.defaults.font.family = getComputedStyle(document.documentElement).getPropertyValue("--font-sans") || "sans-serif";
Chart.defaults.color = "#555d6d";
Chart.defaults.animation = false;
Chart.defaults.plugins.tooltip.backgroundColor = "#1a1c20";
Chart.defaults.plugins.tooltip.padding = 8;

export const COLORS = {
  brand: "#ff6600",
  critical: "#fa342c",
  ready: "#217cf9",
  positive: "#079171",
  band: "#d9f6e9",
  night: "#eeeff1",
  grid: "#eeeff1",
  subtle: "#868b94",
};

/** 밤 구간 음영 플러그인. options.plugins.nightShade.nights = [true/false, …] (x축 칸마다) */
export const nightShade = {
  id: "nightShade",
  beforeDatasetsDraw(chart, _args, opts) {
    const nights = opts?.nights;
    const x = chart.scales.x;
    if (!nights?.length || !x) return;
    const { top, bottom } = chart.chartArea;
    const half = nights.length > 1 ? (x.getPixelForValue(1) - x.getPixelForValue(0)) / 2 : 0;
    const ctx = chart.ctx;
    ctx.save();
    ctx.fillStyle = COLORS.night;
    nights.forEach((n, i) => {
      if (!n) return;
      const cx = x.getPixelForValue(i);
      ctx.fillRect(cx - half, top, half * 2 + 0.5, bottom - top);
    });
    ctx.restore();
  },
};

export { Chart };
