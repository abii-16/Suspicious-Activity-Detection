import { NavLink } from "react-router-dom";
import {
  BarChart3,
  Bot,
  LayoutDashboard,
  Search,
  Shield,
  UserSearch,
} from "lucide-react";

const navItems = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/agent", label: "AI Agent", icon: Bot },
  { to: "/customer", label: "Customer Lookup", icon: UserSearch },
  { to: "/transaction", label: "Transaction Explorer", icon: Search },
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
];

export default function Sidebar() {
  return (
    <aside className="flex h-full w-64 flex-col border-r border-navy-700 bg-navy-900">
      <div className="flex items-center gap-3 border-b border-navy-700 px-5 py-5">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent/20">
          <Shield className="h-5 w-5 text-accent-light" />
        </div>
        <div>
          <p className="text-sm font-semibold text-slate-100">AI AML Agent</p>
          <p className="text-xs text-slate-500">Cybersecurity Dashboard</p>
        </div>
      </div>

      <nav className="flex-1 space-y-1 p-4">
        {navItems.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `sidebar-link ${isActive ? "sidebar-link-active" : ""}`
            }
          >
            <Icon className="h-4 w-4 shrink-0" />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-navy-700 p-4">
        <p className="text-xs text-slate-500">Hackathon Demo v1.0</p>
      </div>
    </aside>
  );
}
