import axios from "axios";
import type {
  CustomerResponse,
  DashboardStats,
  EdaResponse,
  HealthResponse,
  QueryResponse,
  TransactionResponse,
} from "@/types/api";

const api = axios.create({
  baseURL: "/api",
  headers: { "Content-Type": "application/json" },
  timeout: 120_000,
});

export function apiErrorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (err.response?.status === 404) return "Resource not found.";
    if (!err.response) return "Cannot reach backend. Start FastAPI on port 8000.";
    return `Server error (${err.response.status}).`;
  }
  if (err instanceof Error) return err.message;
  return "Request failed.";
}

export async function query(
  userQuery: string,
  conversationHistory: Array<{ query: string; entities?: Record<string, unknown>; natural_response?: string }> = [],
): Promise<QueryResponse> {
  const { data } = await api.post<QueryResponse>("/query", {
    query: userQuery,
    conversation_history: conversationHistory,
  });
  return data;
}

export async function getHealth(): Promise<HealthResponse> {
  const { data } = await api.get<HealthResponse>("/health");
  return data;
}

export async function getDashboard(): Promise<DashboardStats> {
  const { data } = await api.get<DashboardStats>("/dashboard");
  return data;
}

export async function getEda(): Promise<EdaResponse> {
  const { data } = await api.get<EdaResponse>("/eda");
  return data;
}

export async function getCustomer(customerId: number): Promise<CustomerResponse> {
  const { data } = await api.get<CustomerResponse>(`/customer/${customerId}`);
  return data;
}

export async function getTransaction(transactionId: number): Promise<TransactionResponse> {
  const { data } = await api.get<TransactionResponse>(`/transaction/${transactionId}`);
  return data;
}

export default api;
