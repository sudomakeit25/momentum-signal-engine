export type SignalAction = "BUY" | "SELL";

export type SetupType =
  | "ema_crossover"
  | "breakout"
  | "rsi_pullback"
  | "vwap_reclaim"
  | "flag"
  | "flat_base"
  | "tight_consolidation"
  | "gap_up";

export interface Signal {
  symbol: string;
  action: SignalAction;
  setup_type: SetupType;
  reason: string;
  entry: number;
  stop_loss: number;
  target: number;
  rr_ratio: number;
  confidence: number;
  timestamp: string;
}

export interface ScanResult {
  symbol: string;
  price: number;
  change_pct: number;
  volume: number;
  avg_volume: number;
  relative_strength: number;
  score: number;
  signals: Signal[];
  setup_types: SetupType[];
}

export interface PositionSize {
  symbol: string;
  shares: number;
  entry_price: number;
  stop_loss: number;
  target: number;
  dollar_risk: number;
  position_value: number;
  rr_ratio: number;
}

export interface BacktestTrade {
  symbol: string;
  entry_date: string;
  exit_date: string;
  entry_price: number;
  exit_price: number;
  shares: number;
  pnl: number;
  return_pct: number;
}

export interface BacktestResult {
  strategy: string;
  start_date: string;
  end_date: string;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  avg_rr: number;
  total_return_pct: number;
  max_drawdown_pct: number;
  trades: BacktestTrade[];
}

export interface ChartBar {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  ema9: number | null;
  ema21: number | null;
  ema50: number | null;
  ema200: number | null;
  rsi: number | null;
  macd_line: number | null;
  macd_signal: number | null;
  macd_hist: number | null;
  atr: number | null;
  volume_sma20: number | null;
  vwap: number | null;
  rs_vs_spy: number | null;
}

export interface ChartData {
  symbol: string;
  bars: ChartBar[];
  signals: Signal[];
}
