export function normalizeRiskLevel(level: string | undefined): string {
  if (!level) return "LOW";
  return level.trim().toUpperCase();
}

export function riskTone(level: string | undefined): "critical" | "high" | "medium" | "low" {
  const n = normalizeRiskLevel(level);
  if (n.includes("CRIT")) return "critical";
  if (n.includes("HIGH")) return "high";
  if (n.includes("MED")) return "medium";
  return "low";
}

const toneClasses: Record<ReturnType<typeof riskTone>, string> = {
  critical: "border-risk-critical/50 bg-risk-critical/15 text-risk-critical",
  high: "border-risk-high/50 bg-risk-high/15 text-risk-high",
  medium: "border-risk-medium/50 bg-risk-medium/15 text-risk-medium",
  low: "border-risk-low/50 bg-risk-low/15 text-risk-low",
};

const toneDotClasses: Record<ReturnType<typeof riskTone>, string> = {
  critical: "bg-risk-critical shadow-[0_0_8px_rgba(239,68,68,0.8)]",
  high: "bg-risk-high shadow-[0_0_8px_rgba(249,115,22,0.7)]",
  medium: "bg-risk-medium shadow-[0_0_8px_rgba(234,179,8,0.6)]",
  low: "bg-risk-low shadow-[0_0_8px_rgba(34,197,94,0.6)]",
};

export function riskBadgeClasses(level: string | undefined): string {
  return toneClasses[riskTone(level)];
}

export function riskDotClasses(level: string | undefined): string {
  return toneDotClasses[riskTone(level)];
}
