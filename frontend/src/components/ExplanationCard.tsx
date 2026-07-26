import { motion } from "framer-motion";
import { FileSearch } from "lucide-react";

interface ExplanationCardProps {
  explanation: string;
}

export default function ExplanationCard({ explanation }: ExplanationCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, x: 8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: 0.3 }}
      className="rounded-xl border border-accent/25 bg-gradient-to-br from-accent/5 to-navy-900 p-4"
    >
      <div className="mb-2 flex items-center gap-2 text-accent-light">
        <FileSearch className="h-4 w-4" />
        <span className="text-xs font-semibold uppercase tracking-wider">Explanation</span>
      </div>
      <p className="text-sm leading-relaxed text-slate-300">{explanation}</p>
    </motion.div>
  );
}
