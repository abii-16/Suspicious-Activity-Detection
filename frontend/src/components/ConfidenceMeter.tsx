import { motion } from "framer-motion";

interface ConfidenceMeterProps {
  confidence: string;
}

function confidencePercent(value: string): number {
  const normalized = value.trim().toLowerCase();
  if (normalized.includes("high")) return 85;
  if (normalized.includes("medium") || normalized.includes("med")) return 55;
  if (normalized.includes("low")) return 25;
  const numeric = parseFloat(value);
  if (!Number.isNaN(numeric)) return Math.min(100, Math.max(0, numeric));
  return 50;
}

function barColor(percent: number): string {
  if (percent >= 75) return "from-risk-low to-emerald-400";
  if (percent >= 45) return "from-risk-medium to-yellow-400";
  return "from-risk-high to-orange-400";
}

export default function ConfidenceMeter({ confidence }: ConfidenceMeterProps) {
  const percent = confidencePercent(confidence);

  return (
    <div>
      <div className="mb-2 flex items-center justify-between text-sm">
        <span className="font-medium text-slate-200">{confidence || "Medium"}</span>
        <span className="font-mono text-xs text-slate-500">{percent}%</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-navy-800">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${percent}%` }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          className={`h-full rounded-full bg-gradient-to-r ${barColor(percent)}`}
        />
      </div>
    </div>
  );
}
