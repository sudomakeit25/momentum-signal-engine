"use client";

import { RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";

interface ScannerToolbarProps {
  onRefresh: () => void;
  isLoading: boolean;
  autoRefresh: boolean;
  onAutoRefreshChange: (val: boolean) => void;
  dataUpdatedAt: number;
}

export function ScannerToolbar({
  onRefresh,
  isLoading,
  autoRefresh,
  onAutoRefreshChange,
  dataUpdatedAt,
}: ScannerToolbarProps) {
  const ago = dataUpdatedAt
    ? Math.round((Date.now() - dataUpdatedAt) / 1000)
    : null;

  return (
    <div className="flex items-center gap-4">
      <Button
        variant="outline"
        size="sm"
        onClick={onRefresh}
        disabled={isLoading}
        className="gap-2"
      >
        <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? "animate-spin" : ""}`} />
        Refresh
      </Button>

      <div className="flex items-center gap-2">
        <Switch
          id="auto-refresh"
          checked={autoRefresh}
          onCheckedChange={onAutoRefreshChange}
        />
        <Label htmlFor="auto-refresh" className="text-xs text-zinc-400">
          Auto-refresh
        </Label>
      </div>

      {ago !== null && (
        <span className="text-xs text-zinc-500">
          Updated {ago < 5 ? "just now" : `${ago}s ago`}
        </span>
      )}
    </div>
  );
}
