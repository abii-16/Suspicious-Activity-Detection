import { motion } from "framer-motion";
import { riskBadgeClasses, riskDotClasses, normalizeRiskLevel } from "@/utils/risk";

interface RiskBadgeProps {
  level: string;
  size?: "sm" | "md" | "lg";
  pulse?: boolean;
}

export default function RiskBadge({ level, size = "md", pulse = false }: RiskBadgeProps) {
  const label = normalizeRiskLevel(level);
  const sizeClasses =
    size === "sm"
      ? "px-2 py-0.5 text-[10px]"
      : size === "lg"
        ? "px-4 py-1.5 text-sm"
        : "px-2.5 py-1 text-xs";

  return (
    <motion.span
      initial={{ scale: 0.9, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      className={`inline-flex items-center gap-1.5 rounded-full border font-semibold uppercase tracking-wide ${sizeClasses} ${riskBadgeClasses(level)}`}
    >
      <span
        className={`h-1.5 w-1.5 rounded-full ${riskDotClasses(level)} ${pulse ? "animate-pulse" : ""}`}
      />
      {label}
    </motion.span>
  );
}
