import { Search } from "lucide-react";

export default function TransactionExplorerPage() {
  return (
    <div className="page-container">
      <div className="card flex flex-col items-center justify-center gap-3 py-24 text-center">
        <Search className="h-12 w-12 text-accent" />
        <h2 className="text-xl font-semibold text-slate-100">Transaction Explorer</h2>
        <p className="max-w-md text-sm text-slate-400">
          Inspect individual transactions with hybrid ML risk scores and explanations.
        </p>
      </div>
    </div>
  );
}
