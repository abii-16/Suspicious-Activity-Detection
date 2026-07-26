import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { AlertTriangle, BarChart3, Database, Percent } from "lucide-react";
import {
  Bar, BarChart, CartesianGrid, Cell,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { SkeletonCard, SkeletonChart } from "@/components/SkeletonLoader";
import StatCard from "@/components/StatCard";
import { apiErrorMessage, getEda } from "@/services/api";

const COLORS = ["#3b82f6", "#60a5fa", "#2563eb", "#1d4ed8", "#93c5fd", "#0ea5e9", "#0284c7", "#1e40af"];

function toChart(record: Record<string, number> | undefined) {
  if (!record) return [];
  return Object.entries(record).map(([name, value]) => ({ name: String(name), value }));
}

export default function AnalyticsPage() {
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true); setError(null);
      try {
        const eda = await getEda();
        if (!cancelled) setData(eda as unknown as Record<string, unknown>);
      } catch (err) {
        if (!cancelled) setError(apiErrorMessage(err));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  if (loading) return (
    <div className="page-container space-y-6">
      <div className="grid gap-4 sm:grid-cols-4">{Array.from({length:4}).map((_,i)=><SkeletonCard key={i}/>)}</div>
      <div className="grid gap-4 lg:grid-cols-3">{Array.from({length:3}).map((_,i)=><SkeletonChart key={i}/>)}</div>
    </div>
  );

  if (error || !data) return (
    <div className="page-container">
      <div className="card flex items-center gap-3 border-risk-critical/40 text-risk-critical">
        <AlertTriangle className="h-5 w-5"/>
        <p>{error ?? "Failed to load analytics."}</p>
      </div>
    </div>
  );

  // Support both old and new field names
  const totalRows    = (data.total_rows ?? data.rows ?? 0) as number;
  const totalCols    = (data.total_columns ?? 0) as number;
  const fraudPct     = (data.fraud_percentage ?? data.fraud_pct ?? 0) as number;
  const avgFormatted = (data.average_amount_formatted ?? "") as string;
  const avgAmount    = (data.average_amount ?? 0) as number;
  const totalLaunder = (data.total_laundering_transactions ?? 0) as number;
  const summary      = (data.dataset_summary ?? "") as string;

  const topBanks    = data.top_banks as Record<string, number> | undefined;
  const currencies  = (data.top_currencies ?? data.currency_distribution) as Record<string, number> | undefined;
  const formats     = (data.payment_formats ?? data.top_payment_formats) as Record<string, number> | undefined;
  const riskDist    = data.risk_distribution as Record<string, number> | undefined;

  const RISK_COLORS: Record<string, string> = {
    CRITICAL: "#ef4444", HIGH: "#f97316", MEDIUM: "#eab308", LOW: "#22c55e",
  };

  const charts = [
    { title: "Top Banks (by transaction volume)", data: toChart(topBanks) },
    { title: "Top Currencies", data: toChart(currencies) },
    { title: "Payment Formats", data: toChart(formats) },
  ];

  return (
    <div className="page-container space-y-6">
      <motion.div initial={{opacity:0,y:-8}} animate={{opacity:1,y:0}}>
        <h2 className="text-2xl font-bold text-slate-100">Analytics</h2>
        <p className="mt-1 text-sm text-slate-400">Exploratory data analysis — IBM HI-Small AML dataset</p>
      </motion.div>

      {/* Stat cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard title="Total Transactions" value={totalRows.toLocaleString()}
          subtitle={totalCols ? `${totalCols} columns` : undefined} icon={Database} delay={0.05}/>
        <StatCard title="Fraud Rate" value={`${fraudPct}%`}
          subtitle={`${totalLaunder.toLocaleString()} laundering transactions`}
          icon={Percent} delay={0.1} accent="text-risk-high"/>
        <StatCard title="Average Amount" value={avgFormatted || `$${avgAmount.toLocaleString()}`}
          icon={BarChart3} delay={0.15}/>
        <StatCard title="Laundering Txns" value={totalLaunder.toLocaleString()}
          subtitle="Labelled in dataset" icon={AlertTriangle} delay={0.2} accent="text-risk-critical"/>
      </div>

      {/* Summary text */}
      {summary ? (
        <div className="card">
          <h3 className="mb-2 text-sm font-semibold text-slate-200">Dataset Summary</h3>
          <p className="text-sm leading-relaxed text-slate-400">{summary}</p>
        </div>
      ) : null}

      {/* Risk distribution */}
      {riskDist && Object.keys(riskDist).length > 0 ? (
        <motion.div initial={{opacity:0,y:12}} animate={{opacity:1,y:0}} transition={{delay:0.2}} className="card">
          <h3 className="mb-4 text-sm font-semibold text-slate-200">Risk Level Distribution</h3>
          <div className="flex flex-wrap gap-4">
            {Object.entries(riskDist).map(([level, count]) => (
              <div key={level} className="flex-1 min-w-[120px] rounded-lg border border-navy-700 bg-navy-950/50 p-4 text-center">
                <p className="text-xs uppercase tracking-widest text-slate-500">{level}</p>
                <p className="mt-1 text-xl font-bold" style={{color: RISK_COLORS[level] ?? "#64748b"}}>
                  {Number(count).toLocaleString()}
                </p>
              </div>
            ))}
          </div>
        </motion.div>
      ) : null}

      {/* Bar charts */}
      <div className="grid gap-4 lg:grid-cols-3">
        {charts.map((chart, idx) => (
          chart.data.length > 0 ? (
            <motion.div key={chart.title} initial={{opacity:0,y:12}} animate={{opacity:1,y:0}}
              transition={{delay: 0.3 + idx * 0.05}} className="card">
              <h3 className="mb-4 text-sm font-semibold text-slate-200">{chart.title}</h3>
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={chart.data}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#152a45"/>
                  <XAxis dataKey="name" stroke="#64748b" fontSize={10}/>
                  <YAxis stroke="#64748b" fontSize={10}/>
                  <Tooltip contentStyle={{background:"#0a1628",border:"1px solid #152a45",borderRadius:8}}/>
                  <Bar dataKey="value" radius={[4,4,0,0]}>
                    {chart.data.map((_,i)=><Cell key={i} fill={COLORS[i%COLORS.length]}/>)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </motion.div>
          ) : null
        ))}
      </div>
    </div>
  );
}
