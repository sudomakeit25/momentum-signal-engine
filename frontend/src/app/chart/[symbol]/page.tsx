import ChartClient from "./chart-client";

// Pre-generate pages for the default universe symbols.
// CloudFront's SPA fallback handles any symbol not listed here.
const UNIVERSE = [
  "AAPL","MSFT","GOOGL","AMZN","NVDA","META","AMD","AVGO","QCOM","INTC","MU","ORCL","CRM","ADBE","NFLX",
  "LRCX","KLAC","AMAT","MRVL","ON","SWKS","TXN","NOW","INTU","WDAY","TEAM","ZM","OKTA","MDB","HUBS",
  "SQ","PYPL","COIN","SOFI","SHOP","PLTR","SNOW","DDOG","NET","CRWD","ZS","PANW",
  "TSLA","ABNB","UBER","DASH","RBLX","U","TTD","NKE","SBUX","MCD","HD","LOW","TGT",
  "WMT","COST","PG","KO","PEP","CL","EL","MNST",
  "XOM","CVX","COP","SLB","OXY","DVN","MPC","PSX","EOG","HES","VLO","HAL","ENPH","SEDG","FSLR","CEG",
  "LLY","UNH","JNJ","PFE","ABBV","MRK","BMY","AMGN","TMO","ABT","DHR","ISRG","MDT","GILD","VRTX","REGN",
  "JPM","BAC","GS","MS","WFC","C","SCHW","BLK","AXP","COF","ICE","CME","SPGI","MMC",
  "CAT","DE","HON","GE","RTX","LMT","BA","NOC","UNP","UPS","FDX","WM","EMR","ITW",
  "DIS","CMCSA","T","VZ","CHTR","TMUS","AMT","PLD","CCI","EQIX","NEE","DUK","SO","AEP",
  "LIN","APD","SHW","ECL","NEM","FCX","MARA","RIOT",
  "SPY","QQQ","IWM","DIA","XLF","XLE","XLK","XLV",
];

export function generateStaticParams() {
  return UNIVERSE.map((s) => ({ symbol: s }));
}

export default function ChartPage() {
  return <ChartClient />;
}
