"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  ScanSearch,
  CandlestickChart,
  Calculator,
  BarChart3,
  Activity,
  BookOpen,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/scanner", label: "Scanner", icon: ScanSearch },
  { href: "/chart/SPY", label: "Charts", icon: CandlestickChart },
  { href: "/position-sizer", label: "Position Sizer", icon: Calculator },
  { href: "/backtest", label: "Backtest", icon: BarChart3 },
  { href: "/guide", label: "Guide", icon: BookOpen },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 z-40 flex h-screen w-60 flex-col border-r border-zinc-800 bg-zinc-950">
      <div className="flex h-14 items-center gap-2 border-b border-zinc-800 px-4">
        <Activity className="h-5 w-5 text-cyan-400" />
        <span className="text-sm font-bold tracking-tight text-zinc-100">
          Momentum Engine
        </span>
      </div>

      <nav className="flex-1 space-y-1 p-3">
        {NAV_ITEMS.map((item) => {
          const isActive =
            pathname === item.href || pathname.startsWith(item.href.split("/").slice(0, 2).join("/"));
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "border-l-2 border-cyan-400 bg-zinc-800/50 text-cyan-400"
                  : "text-zinc-400 hover:bg-zinc-800/30 hover:text-zinc-200"
              )}
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-zinc-800 p-4">
        <div className="flex items-center gap-2 text-xs text-zinc-500">
          <span className="h-2 w-2 rounded-full bg-emerald-500" />
          MSE v0.1.0
        </div>
      </div>
    </aside>
  );
}
