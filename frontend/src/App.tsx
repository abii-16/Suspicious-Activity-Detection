import { Navigate, Route, Routes } from "react-router-dom";
import AppLayout from "./components/layout/AppLayout";
import AgentPage from "./pages/AgentPage";
import AnalyticsPage from "./pages/AnalyticsPage";
import CustomerLookupPage from "./pages/CustomerLookupPage";
import DashboardPage from "./pages/DashboardPage";
import TransactionExplorerPage from "./pages/TransactionExplorerPage";

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<DashboardPage />} />
        <Route path="agent" element={<AgentPage />} />
        <Route path="customer" element={<CustomerLookupPage />} />
        <Route path="transaction" element={<TransactionExplorerPage />} />
        <Route path="analytics" element={<AnalyticsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
