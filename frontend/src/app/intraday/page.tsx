"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { AlertTriangle, Zap } from "lucide-react";
import { useIntraday } from "@/hooks/use-intraday";
import { SetupTypeBadge } from "@/components/scanner/setup-type-badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";
import type { IntradayResult, Signal } from "@/types/api";

const EARNINGS_KEY = "mse-earnings-dates";

function earningsSoonSymbols(): Set<string> {
  if (typeof window === "undefined") return new Set();
  try {
    const entries: { symbol: string; date: string }[] = JSON.parse(
      localStorage.getItem(EARNINGS_KEY) || "[]"
    );
    const out = new Set<string>();
    const now = new Date();
    now.setHours(0, 0, 0, 0);
    for (const e of entries) {
      const d = new Date(e.date);
      d.setHours(0, 0, 0, 0);
      const days = Math.ceil((d.getTime() - now.getTime()) / 86_400_000);
      if (days >= 0 && days <= 1) out.add(e.symbol.toUpperCase());
    }
    return out;
  } catch {
    return new Set();
  }
}

function bestSignal(r: IntradayResult): Signal | null {
  if (!r.signals.length) return null;
  return [...r.signals].sort((a, b) => b.confidence - a.confidence)[0];
}

function fmtVol(v: number): string {
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000) return `${(v / 1_000).toFixed(0)}K`;
  return String(v);
}

export default function IntradayPage() {
  const [minChange, setMinChange] = useState(2);
  const [minRvol, setMinRvol] = useState(1.5);
  const [minPrice, setMinPrice] = useState(20);
  const { data, isLoading, dataUpdatedAt } = useIntraday({
    min_change_pct: minChange,
    min_rvol: minRvol,
    min_price: minPrice,
  });
  const earningsSoon = useMemo(earningsSoonSymbols, [dataUpdatedAt]);

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <Zap className="h-5 w-5 text-amber-400" />
          <h1 className="text-lg font-bold">Intraday Movers</h1>
          <span className="text-xs text-muted-foreground">
            liquidity + volatility + a trigger · 5-min bars, today only
          </span>
        </div>
        <div className="flex items-end gap-3">
          <div>
            <Label className="text-xs">Min |chg| %</Label>
            <Input
              type="number" step="0.5" value={minChange} className="h-8 w-20"
              onChange={(e) => setMinChange(Number(e.target.value))}
            />
          </div>
          <div>
            <Label className="text-xs">Min RVOL</Label>
            <Input
              type="number" step="0.25" value={minRvol} className="h-8 w-20"
              onChange={(e) => setMinRvol(Number(e.target.value))}
            />
          </div>
          <div>
            <Label className="text-xs">Min price</Label>
            <Input
              type="number" step="5" value={minPrice} className="h-8 w-20"
              onChange={(e) => setMinPrice(Number(e.target.value))}
            />
          </div>
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
        </div>
      ) : !data || data.length === 0 ? (
        <div className="rounded-lg border border-dashed p-10 text-center text-sm text-muted-foreground">
          No qualifying movers right now. Outside market hours this is
          expected — the screen only looks at today&apos;s session.
        </div>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Symbol</TableHead>
              <TableHead className="text-right">Price</TableHead>
              <TableHead className="text-right">Chg%</TableHead>
              <TableHead className="text-right">RVOL</TableHead>
              <TableHead className="text-right">ATR%</TableHead>
              <TableHead className="text-right">Spread%</TableHead>
              <TableHead className="text-right">VWAP dist</TableHead>
              <TableHead className="text-right">Vol</TableHead>
              <TableHead>Setups</TableHead>
              <TableHead className="text-right">Entry / Stop / Target</TableHead>
              <TableHead className="text-right">R:R</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.map((r) => {
              const sig = bestSignal(r);
              const ern = earningsSoon.has(r.symbol);
              return (
                <TableRow key={r.symbol}>
                  <TableCell className="font-medium">
                    <div className="flex items-center gap-1.5">
                      <Link href={`/chart/${r.symbol}`} className="hover:underline">
                        {r.symbol}
                      </Link>
                      {ern && (
                        <span
                          title="Earnings within a day — be flat before the close"
                          className="inline-flex items-center gap-0.5 rounded border border-yellow-500/30 bg-yellow-500/20 px-1 text-[10px] text-yellow-400"
                        >
                          <AlertTriangle className="h-3 w-3" /> ERN
                        </span>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="text-right">${r.price.toFixed(2)}</TableCell>
                  <TableCell
                    className={cn(
                      "text-right font-medium",
                      r.change_pct >= 0 ? "text-emerald-400" : "text-red-400"
                    )}
                  >
                    {r.change_pct >= 0 ? "+" : ""}
                    {r.change_pct.toFixed(2)}%
                  </TableCell>
                  <TableCell className="text-right">{r.rvol.toFixed(1)}x</TableCell>
                  <TableCell className="text-right">{r.atr_pct.toFixed(1)}%</TableCell>
                  <TableCell className="text-right text-muted-foreground">
                    {r.spread_pct == null ? "–" : `${r.spread_pct.toFixed(3)}%`}
                  </TableCell>
                  <TableCell
                    className={cn(
                      "text-right",
                      r.vwap_dist_pct >= 0 ? "text-emerald-400" : "text-red-400"
                    )}
                  >
                    {r.vwap_dist_pct >= 0 ? "+" : ""}
                    {r.vwap_dist_pct.toFixed(2)}%
                  </TableCell>
                  <TableCell className="text-right text-muted-foreground">
                    {fmtVol(r.volume)}
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {r.setup_types.map((t) => (
                        <SetupTypeBadge key={t} type={t} />
                      ))}
                    </div>
                  </TableCell>
                  <TableCell className="text-right text-xs tabular-nums">
                    {sig
                      ? `${sig.entry.toFixed(2)} / ${sig.stop_loss.toFixed(2)} / ${sig.target.toFixed(2)}`
                      : "–"}
                  </TableCell>
                  <TableCell className="text-right">
                    {sig ? (
                      <span className="font-medium text-cyan-400">
                        {sig.rr_ratio.toFixed(1)}
                      </span>
                    ) : (
                      "–"
                    )}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      )}

      <div className="rounded-lg border bg-muted/30 p-3 text-xs text-muted-foreground">
        <strong>Checklist before entry:</strong> spread + slippage &lt; 0.1% ·
        a reason it&apos;s moving (news, sector, earnings) · R:R at least 1:1.5 ·
        know exactly where you&apos;re wrong (stop under the higher low / box) ·
        flat before the close on anything reporting tonight (track dates on the{" "}
        <Link href="/earnings" className="underline">Earnings</Link> page).
        Setups shown: {" "}
        <em>Range Break</em> (tight 30-60 min box resolving on volume),{" "}
        <em>VWAP Reclaim/Reject</em> (institutional reference line), {" "}
        <em>Higher Low</em> (afternoon pullback holding above the morning low).
      </div>
    </div>
  );
}
