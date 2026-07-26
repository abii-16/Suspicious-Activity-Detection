import type { ComponentType, ReactNode } from "react";
import { motion } from "framer-motion";

interface StatCardProps {
  title: string;
  value: ReactNode;
  subtitle?: string;
  icon: ComponentType<{ className?: string }>;
  delay?: number;
  accent?: string;
}

export default function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  delay = 0,
  accent = "text-accent-light",
}: StatCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.35 }}
      className="card relative overflow-hidden"
    >
      <div className="pointer-events-none absolute -right-4 -top-4 h-20 w-20 rounded-full bg-accent/5" />
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-widest text-slate-500">{title}</p>
          <p className="mt-2 text-2xl font-bold text-slate-100">{value}</p>
          {subtitle ? <p className="mt-1 text-xs text-slate-500">{subtitle}</p> : null}
        </div>
        <div className={`rounded-lg border border-navy-600 bg-navy-800/80 p-2.5 ${accent}`}>
          <Icon className="h-5 w-5" />
        </div>
      </div>
    </motion.div>
  );
}
