const BASE_URL = '/api/v1';

export interface WardRisk {
  ward_id: string;
  ward_name: string;
  zone: string;
  hazard: number;
  hazard_band: string;
  exposure: number;
  vulnerability: number;
  impact: number;
  risk_score: number;
  risk_level: string;
  safety_floor_triggered?: string | null;
  confidence: number;
  is_abstained: boolean;
  is_simulated: boolean;
  feature_contributions?: Record<string, number>;
}

export interface PendingReview {
  case_id: string;
  assessment_id: string;
  ward_id: string;
  risk_level: string;
  status: string;
  created_at: string;
  expires_at?: string;
  content_hash: string;
}

export interface DemoState {
  scenario_id: string;
  current_step: number;
  phase: string;
  water_levels: Record<string, number>;
  is_simulated: boolean;
}

export interface RouteResult {
  status: string;
  route_nodes: string[];
  distance_m: number;
  duration_s: number;
  duration_min: number;
  srs_score: number;
  max_edge_risk: number;
  mean_edge_risk: number;
  message?: string;
}

async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });
  if (!response.ok) {
    let errMsg = response.statusText;
    try {
      const errJson = await response.json();
      errMsg = errJson.detail || errJson.message || errMsg;
    } catch {
      // fallback
    }
    throw new Error(`API Error [${response.status}]: ${errMsg}`);
  }
  return response.json();
}

export const apiClient = {
  // Risk
  fetchRisk: () => fetchApi<WardRisk[]>('/risk'),
  fetchWardRisk: (wardId: string) => fetchApi<WardRisk>(`/risk/${wardId}`),

  // Zones & Geospatial
  fetchZones: () => fetchApi<any>('/zones'),
  fetchZoneById: (wardId: string) => fetchApi<any>(`/zones/${wardId}`),

  // Assessments & Explanation
  fetchAssessments: () => fetchApi<any[]>('/assessments'),
  fetchAssessmentDetail: (id: string) => fetchApi<any>(`/assessments/${id}`),
  triggerAssessment: (wardId: string) =>
    fetchApi<any>('/assessments', { method: 'POST', body: JSON.stringify({ ward_id: wardId }) }),
  fetchExplanation: (assessmentId: string) => fetchApi<any>(`/explanations/${assessmentId}`),

  // Reviews & Approval State Machine
  fetchPendingReviews: () => fetchApi<PendingReview[]>('/reviews/pending'),
  approveReview: (caseId: string, reviewerId: string, rationale: string, checklist: Record<string, boolean>) =>
    fetchApi<any>(`/reviews/${caseId}/approve`, {
      method: 'POST',
      body: JSON.stringify({ reviewer_id: reviewerId, rationale, checklist, reviewer_role: 'EMERGENCY_COORDINATOR' }),
    }),
  rejectReview: (caseId: string, reviewerId: string, rationale: string) =>
    fetchApi<any>(`/reviews/${caseId}/reject`, {
      method: 'POST',
      body: JSON.stringify({ reviewer_id: reviewerId, rationale }),
    }),

  // Alerts
  fetchAlerts: () => fetchApi<any[]>('/alerts'),
  dispatchAlert: (caseId: string, message?: string) =>
    fetchApi<any>(`/alerts/${caseId}/dispatch`, {
      method: 'POST',
      body: JSON.stringify({ message }),
    }),

  // Routing
  calculateRoute: (origin: string, destination: string, overlay?: Record<string, number>) =>
    fetchApi<RouteResult>('/routes', {
      method: 'POST',
      body: JSON.stringify({
        origin_node: origin,
        destination_node: destination,
        flood_penalty_overlay: overlay,
      }),
    }),

  // Demo & Simulation Control
  getDemoState: () => fetchApi<DemoState>('/demo/state'),
  controlDemo: (action: string) =>
    fetchApi<any>('/demo/control', {
      method: 'POST',
      body: JSON.stringify({ action }),
    }),

  // Ingested Telemetry
  fetchRainfall: () => fetchApi<any[]>('/data/rainfall'),
  fetchWaterLevels: () => fetchApi<any[]>('/data/water-level'),
  fetchDataQuality: () => fetchApi<any>('/data/quality'),

  // Forecasts
  fetchForecasts: (wardId?: string) =>
    fetchApi<any>(wardId ? `/forecasts?ward_id=${encodeURIComponent(wardId)}` : '/forecasts'),

  // Recommendations
  fetchRecommendations: (assessmentId?: string) =>
    fetchApi<any[]>(
      assessmentId
        ? `/recommendations?assessment_id=${encodeURIComponent(assessmentId)}`
        : '/recommendations'
    ),

  // Audit Log & Verification
  fetchAuditLog: () => fetchApi<any[]>('/audit'),
  verifyAuditChain: () => fetchApi<any>('/audit/verify', { method: 'POST' }),
};
