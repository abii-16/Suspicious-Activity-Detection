import { Loader2 } from "lucide-react";

interface LoadingSpinnerProps {
  label?: string;
  size?: "sm" | "md";
}

export default function LoadingSpinner({ label, size = "md" }: LoadingSpinnerProps) {
  const iconClass = size === "sm" ? "h-4 w-4" : "h-6 w-6";

  return (
    <div className="flex items-center gap-2 text-slate-400">
      <Loader2 className={`${iconClass} animate-spin text-accent`} />
      {label ? <span className="text-sm">{label}</span> : null}
    </div>
  );
}
