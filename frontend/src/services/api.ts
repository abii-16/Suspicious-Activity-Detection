import axios from "axios";
import type { QueryResponse } from "@/types/api";

const api = axios.create({
  baseURL: "/api",
  headers: { "Content-Type": "application/json" },
  timeout: 120_000,
});

export function apiErrorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (err.response?.status === 404) return "Endpoint not found.";
    if (!err.response) return "Cannot reach backend. Start FastAPI on port 8000.";
    return `Server error (${err.response.status}).`;
  }
  if (err instanceof Error) return err.message;
  return "Request failed.";
}

export async function query(userQuery: string): Promise<QueryResponse> {
  const { data } = await api.post<QueryResponse>("/query", { query: userQuery });
  return data;
}

export default api;
