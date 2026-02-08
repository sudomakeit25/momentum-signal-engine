"use client";

import { useEffect, useRef } from "react";
import {
  createChart,
  ColorType,
  CrosshairMode,
  CandlestickSeries,
  LineSeries,
  type IChartApi,
  type Time,
} from "lightweight-charts";
import type { ChartBar, Signal } from "@/types/api";

interface CandlestickChartProps {
  bars: ChartBar[];
  signals: Signal[];
  showEma9?: boolean;
  showEma21?: boolean;
  showEma50?: boolean;
  showEma200?: boolean;
  showVwap?: boolean;
}

function toTime(ts: string): Time {
  return ts.split("T")[0] as Time;
}

export function CandlestickChart({
  bars,
  signals,
  showEma9 = true,
  showEma21 = true,
  showEma50 = false,
  showEma200 = false,
  showVwap = false,
}: CandlestickChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!containerRef.current || bars.length === 0) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#71717a",
      },
      grid: {
        vertLines: { color: "#27272a" },
        horzLines: { color: "#27272a" },
      },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: "#3f3f46" },
      timeScale: { borderColor: "#3f3f46" },
      width: containerRef.current.clientWidth,
      height: 420,
    });
    chartRef.current = chart;

    // Candlestick series
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#22c55e",
      downColor: "#ef4444",
      borderDownColor: "#ef4444",
      borderUpColor: "#22c55e",
      wickDownColor: "#ef4444",
      wickUpColor: "#22c55e",
    });

    candleSeries.setData(
      bars.map((b) => ({
        time: toTime(b.timestamp),
        open: b.open,
        high: b.high,
        low: b.low,
        close: b.close,
      }))
    );

    // EMA overlays
    const addLine = (
      values: (number | null)[],
      color: string,
      show: boolean
    ) => {
      if (!show) return;
      const series = chart.addSeries(LineSeries, {
        color,
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      const data = bars
        .map((b, i) =>
          values[i] !== null
            ? { time: toTime(b.timestamp), value: values[i]! }
            : null
        )
        .filter((d): d is { time: Time; value: number } => d !== null);
      series.setData(data);
    };

    addLine(bars.map((b) => b.ema9), "#06b6d4", showEma9);
    addLine(bars.map((b) => b.ema21), "#eab308", showEma21);
    addLine(bars.map((b) => b.ema50), "#f97316", showEma50);
    addLine(bars.map((b) => b.ema200), "#ef4444", showEma200);
    addLine(bars.map((b) => b.vwap), "#a855f7", showVwap);

    // Signal markers as price lines on the candlestick series
    for (const s of signals) {
      candleSeries.createPriceLine({
        price: s.entry,
        color: s.action === "BUY" ? "#22c55e80" : "#ef444480",
        lineWidth: 1,
        lineStyle: 2,
        axisLabelVisible: false,
        title: s.action,
      });
    }

    chart.timeScale().fitContent();

    const handleResize = () => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
    };
  }, [bars, signals, showEma9, showEma21, showEma50, showEma200, showVwap]);

  return <div ref={containerRef} className="w-full" />;
}
