import { motion } from "framer-motion";
import { ShieldAlert } from "lucide-react";

interface RecommendationCardProps {
  recommendation: string;
}

export default function RecommendationCard({ recommendation }: RecommendationCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: 0.25 }}
      className="rounded-xl border border-risk-high/30 bg-gradient-to-br from-risk-high/10 to-navy-900 p-4"
    >
      <div className="mb-2 flex items-center gap-2 text-risk-high">
        <ShieldAlert className="h-4 w-4" />
        <span className="text-xs font-semibold uppercase tracking-wider">Recommendation</span>
      </div>
      <p className="text-sm leading-relaxed text-slate-200">{recommendation}</p>
    </motion.div>
  );
}
