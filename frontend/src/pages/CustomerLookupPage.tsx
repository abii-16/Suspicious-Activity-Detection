import { UserSearch } from "lucide-react";

export default function CustomerLookupPage() {
  return (
    <div className="page-container">
      <div className="card flex flex-col items-center justify-center gap-3 py-24 text-center">
        <UserSearch className="h-12 w-12 text-accent" />
        <h2 className="text-xl font-semibold text-slate-100">Customer Lookup</h2>
        <p className="max-w-md text-sm text-slate-400">
          Search customers by ID to view risk profiles and transaction history.
        </p>
      </div>
    </div>
  );
}
