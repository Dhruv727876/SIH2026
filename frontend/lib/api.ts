import axios from "axios";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export const apiClient = axios.create({
  baseURL: API_BASE_URL.endsWith("/api/v1")
    ? API_BASE_URL
    : `${API_BASE_URL.replace(/\/$/, "")}/api/v1`,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 15000,
});

export interface ForecastItem {
  timestamp: string;
  predicted_value: number;
  lower_bound: number;
  upper_bound: number;
}

export interface ForecastResponse {
  index_name: string;
  forecast_horizon_days: number;
  generated_at: string;
  forecast: ForecastItem[];
}

export interface OptimizationRequest {
  required_cargo_mt: number;
  target_port: string;
  origin_port?: string;
  planning_horizon_days: number;
  disruption_multiplier?: number;
  disruption_name?: string;
}

export interface VesselScheduleItem {
  date: string;
  vessel_type: string;
  quantity: number;
  capacity_mt?: number;
  total_cargo_mt?: number;
  freight_rate_usd_mt?: number;
  estimated_trip_cost_usd?: number;
}

export interface OptimizationResponse {
  status: string;
  target_port?: string;
  origin_port?: string;
  route?: string;
  port_max_draft_m?: number;
  port_waiting_hours?: number;
  required_cargo_mt?: number;
  total_cargo_allocated_mt?: number;
  total_estimated_cost_usd: number;
  estimated_savings_usd: number;
  benchmark_naive_cost_usd?: number;
  vessel_schedule: VesselScheduleItem[];
  message?: string;
  active_disruption_name?: string;
  disruption_multiplier?: number;
}

export interface PortDataResponse {
  id: number;
  port_name: string;
  max_draft_meters: number;
  current_waiting_time_hours: number;
  updated_at: string;
}

export interface DisruptionEvent {
  event_id: number;
  date: string;
  event_type: string;
  event_name: string;
  category?: string;
  affected_region: string;
  bdi_impact_pct: number;
  freight_shock_multiplier: number;
  description: string;
}

export interface DisruptionMultiplierResponse {
  event_type: string;
  freight_shock_multiplier: number;
  spike_percentage: number;
}

/**
 * Fetch 60-day freight/bunker forecast for a specified index.
 */
export async function fetchForecast(indexName: string): Promise<ForecastResponse> {
  const response = await apiClient.get<ForecastResponse>(`/forecasts/${indexName}`);
  return response.data;
}

/**
 * Run MILP vessel chartering optimization with Route Distance Multipliers.
 */
export async function runOptimization(
  payload: OptimizationRequest
): Promise<OptimizationResponse> {
  const response = await apiClient.post<OptimizationResponse>("/optimize", payload);
  return response.data;
}

/**
 * Fetch latest port draft and congestion telemetry.
 */
export async function fetchPortData(portName?: string): Promise<PortDataResponse[]> {
  const params = portName ? { port_name: portName } : {};
  const response = await apiClient.get<PortDataResponse[]>("/port-data", { params });
  return response.data;
}

/**
 * Fetch list of historical supply chain and maritime disruption events.
 */
export async function fetchDisruptions(): Promise<DisruptionEvent[]> {
  const response = await apiClient.get<DisruptionEvent[]>("/disruptions");
  return response.data;
}

/**
 * Fetch specific freight rate spike multiplier for a disruption type.
 */
export async function getDisruptionMultiplier(
  eventType: string
): Promise<DisruptionMultiplierResponse> {
  const response = await apiClient.get<DisruptionMultiplierResponse>(
    `/disruptions/${eventType}/multiplier`
  );
  return response.data;
}
