import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  BarChart3,
  Percent,
  ShieldAlert,
  TrendingUp,
  Wallet,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import RiskBadge from "@/components/RiskBadge";
import { SkeletonCard, SkeletonChart, SkeletonTable } from "@/components/SkeletonLoader";
import StatCard from "@/components/StatCard";
import { apiErrorMessage, getDashboard } from "@/services/api";
import type { DashboardStats } from "@/types/api";

const RISK_COLORS: Record<string, string> = {
  CRITICAL: "#ef4444",
  HIGH: "#f97316",
  MEDIUM: "#eab308",
  LOW: "#22c55e",
};

const CHART_COLORS = ["#3b82f6", "#60a5fa", "#2563eb", "#1d4ed8", "#93c5fd", "#1e40af", "#0ea5e9", "#0284c7"];

function formatNumber(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return value.toLocaleString();
}

function recordToChartData(record: Record<string, number>, labelKey = "name") {
  return Object.entries(record).map(([key, value]) => ({
    [labelKey]: key,
    value,
  }));
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const stats = await getDashboard();
        if (!cancelled) setData(stats);
      } catch (err) {
        if (!cancelled) setError(apiErrorMessage(err));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void load();
  }, []);

  if (loading) {
    return (
      <div className="page-container space-y-6">
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
          {Array.from({ length: 5 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          <SkeletonChart />
          <SkeletonChart />
        </div>
        <SkeletonTable />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="page-container">
        <div className="card flex items-center gap-3 border-risk-critical/40 text-risk-critical">
          <AlertTriangle className="h-5 w-5" />
          <p>{error ?? "Failed to load dashboard."}</p>
        </div>
      </div>
    );
  }

  const riskDistribution = Object.entries(data.risk_distribution).map(([name, value]) => ({
    name,
    value,
    fill: RISK_COLORS[name] ?? "#64748b",
  }));

  return (
    <div className="page-container space-y-6">
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}>
        <h2 className="text-2xl font-bold text-slate-100">Risk Overview</h2>
        <p className="mt-1 text-sm text-slate-400">
          Real-time AML intelligence across {formatNumber(data.total_transactions)} transactions
        </p>
      </motion.div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <StatCard
          title="Total Transactions"
          value={formatNumber(data.total_transactions)}
          icon={Wallet}
          delay={0.05}
        />
        <StatCard
          title="High Risk"
          value={formatNumber(data.high_risk_count)}
          icon={ShieldAlert}
          delay={0.1}
          accent="text-risk-high"
        />
        <StatCard
          title="Critical Risk"
          value={formatNumber(data.critical_risk_count)}
          icon={AlertTriangle}
          delay={0.15}
          accent="text-risk-critical"
        />
        <StatCard
          title="Average Risk Score"
          value={data.average_risk_score.toFixed(4)}
          icon={TrendingUp}
          delay={0.2}
        />
        <StatCard
          title="Flagged %"
          value={`${data.flagged_pct}%`}
          subtitle="Labelled as laundering"
          icon={Percent}
          delay={0.25}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="card"
        >
          <div className="mb-4 flex items-center gap-2">
            <BarChart3 className="h-4 w-4 text-accent" />
            <h3 className="text-sm font-semibold text-slate-200">Risk Distribution</h3>
          </div>
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie
                data={riskDistribution}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                innerRadius={55}
                outerRadius={90}
                paddingAngle={2}
              >
                {riskDistribution.map((entry) => (
                  <Cell key={entry.name} fill={entry.fill} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  background: "#0a1628",
                  border: "1px solid #152a45",
                  borderRadius: 8,
                }}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="mt-2 flex flex-wrap justify-center gap-3">
            {riskDistribution.map((item) => (
              <span key={item.name} className="flex items-center gap-1.5 text-xs text-slate-400">
                <span className="h-2 w-2 rounded-full" style={{ background: item.fill }} />
                {item.name}: {formatNumber(item.value)}
              </span>
            ))}
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25 }}
          className="card"
        >
          <div className="mb-4 flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-accent" />
            <h3 className="text-sm font-semibold text-slate-200">Risk Trend by Month</h3>
          </div>
          {data.risk_trend.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={data.risk_trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#152a45" />
                <XAxis dataKey="month" stroke="#64748b" fontSize={11} />
                <YAxis stroke="#64748b" fontSize={11} domain={[0, 1]} />
                <Tooltip
                  contentStyle={{
                    background: "#0a1628",
                    border: "1px solid #152a45",
                    borderRadius: 8,
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="avg_risk_score"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  dot={{ fill: "#60a5fa", r: 3 }}
                  name="Avg Risk Score"
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <p className="py-16 text-center text-sm text-slate-500">Trend data unavailable.</p>
          )}
        </motion.div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        {[
          { title: "Top Banks", data: recordToChartData(data.top_banks) },
          { title: "Currency Distribution", data: recordToChartData(data.currency_distribution) },
          {
            title: "Payment Format Distribution",
            data: recordToChartData(data.payment_format_distribution),
          },
        ].map((chart, idx) => (
          <motion.div
            key={chart.title}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 + idx * 0.05 }}
            className="card"
          >
            <h3 className="mb-4 text-sm font-semibold text-slate-200">{chart.title}</h3>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={chart.data.slice(0, 8)}>
                <CartesianGrid strokeDasharray="3 3" stroke="#152a45" />
                <XAxis dataKey="name" stroke="#64748b" fontSize={10} />
                <YAxis stroke="#64748b" fontSize={10} />
                <Tooltip
                  contentStyle={{
                    background: "#0a1628",
                    border: "1px solid #152a45",
                    borderRadius: 8,
                  }}
                />
                <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                  {chart.data.slice(0, 8).map((_, i) => (
                    <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </motion.div>
        ))}
      </div>

      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.45 }}
        className="card overflow-hidden p-0"
      >
        <div className="border-b border-navy-700 px-5 py-4">
          <h3 className="text-sm font-semibold text-slate-200">Top Suspicious Transactions</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead>
              <tr className="border-b border-navy-700 text-xs uppercase tracking-wide text-slate-500">
                <th className="px-5 py-3 font-medium">Txn ID</th>
                <th className="px-5 py-3 font-medium">Account</th>
                <th className="px-5 py-3 font-medium">Amount</th>
                <th className="px-5 py-3 font-medium">Score</th>
                <th className="px-5 py-3 font-medium">Risk</th>
                <th className="px-5 py-3 font-medium">Pattern</th>
              </tr>
            </thead>
            <tbody>
              {data.top_suspicious_transactions.map((tx) => (
                <tr key={tx.transaction_id} className="border-b border-navy-800/80 hover:bg-navy-800/40">
                  <td className="px-5 py-3 font-mono text-accent-light">{tx.transaction_id}</td>
                  <td className="px-5 py-3 font-mono text-slate-300">{tx.account ?? "—"}</td>
                  <td className="px-5 py-3 text-slate-300">
                    {tx.amount_paid != null ? tx.amount_paid.toLocaleString() : "—"}
                  </td>
                  <td className="px-5 py-3 font-mono text-slate-300">{tx.risk_score}</td>
                  <td className="px-5 py-3">
                    <RiskBadge level={tx.risk_level} size="sm" />
                  </td>
                  <td className="max-w-xs truncate px-5 py-3 text-xs text-slate-400">
                    {tx.aml_pattern ?? tx.recommended_action ?? "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </motion.div>
    </div>
  );
}
