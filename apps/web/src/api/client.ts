const BASE_URL = '/api/v1';

export interface WardRisk {
  ward_id: string;
  ward_name: string;
  zone?: string | null;
  zone_join_status?: string | null;
  hazard: number | null;
  hazard_band: string | null;
  exposure: number | null;
  vulnerability: number | null;
  impact: number | null;
  risk_score: number | null;
  risk_level: string;
  safety_floor_triggered?: string | null;
  confidence: number | null;
  is_abstained: boolean;
  is_simulated: boolean;
  abstention_reason?: string;
  data_classification?: string;
  feature_contributions?: Record<string, number>;
}

export interface PendingReview {
  case_id: string;
  assessment_id: string;
  ward_id: string;
  ward_name?: string;
  zone?: string;
  risk_level: string;
  status: string;
  created_at: string;
  expires_at?: string;
  content_hash: string;
  action_id?: string;
  action_title?: string;
  action_description?: string;
  department?: string;
  authority_of_control?: string;
  urgency?: string;
  priority?: string;
}

export interface DemoState {
  scenario_id: string;
  fixture_sha256: string;
  assessment_reference: string;
  name: string;
  description: string;
  data_classification: 'SIMULATED_SCENARIO';
  assumption_note: string;
  current_step: number;
  max_step: number;
  peak_step: number;
  phase: string;
  is_simulated: boolean;
  assessment: {
    status: 'SIMULATED_SCENARIO_ONLY';
    is_simulated: true;
    data_classification: string;
    ward_id: string;
    config_version: string;
    fixture_sha256: string;
    summary: {
      step: number;
      time_offset_min: number;
      phase: string;
      rainfall_intensity_mmh: number;
      water_level_m: number;
      hazard: number;
      hazard_band: string;
      risk_level: string;
      risk_score: number;
    };
    inputs: Record<string, number>;
    exposure: number;
    vulnerability: number;
    impact: number;
    risk_level: string;
    risk_score: number;
    hazard: number;
    hazard_band: string;
    safety_floor_triggered: string | null;
    confidence: null;
    confidence_note: string;
    explanation: {
      method: string;
      causal_claim: false;
      factors: Array<{ feature: string; input_value: number; weighted_ramp_term: number }>;
    };
    recommendations: Array<{
      type: string;
      text: string;
      status: 'DRAFT';
      approval_required: true;
      is_simulated: true;
      catalogue_id: string;
      scope: 'SIMULATED_EXERCISE_ONLY';
      affected_ward: string;
      urgency: 'EXERCISE_ONLY';
      reason: string;
      assumptions: string[];
      confidence: null;
      evidence_requirements: string[];
    }>;
    limitations: string[];
  };
  timeline: Array<{
    step: number;
    time_offset_min: number;
    phase: string;
    rainfall_intensity_mmh: number;
    water_level_m: number;
    hazard: number;
    hazard_band: string;
    risk_level: string;
    risk_score: number;
  }>;
}

export interface RouteResult {
  status: string;
  is_simulated: true;
  prototype_only: true;
  network_basis: 'SYNTHETIC_DEMONSTRATION_GRAPH';
  safety_decision: 'NOT_EVALUATED';
  limitations: string[];
  route_nodes: string[];
  distance_m: number;
  duration_s: number;
  duration_min: number;
  srs_score: number;
  max_edge_risk: number;
  mean_edge_risk: number;
  message?: string;
}

export interface RoutingNode {
  id: string;
  name: string;
  pos: [number, number];
  sector: string;
  zone: string;
  is_shelter: boolean;
  vulnerability?: number;
  est_evacuees?: number;
}

export interface RoutingShelter {
  id: string;
  name: string;
  pos: [number, number];
  sector: string;
  zone: string;
  is_shelter: true;
  safety: number;
  capacity: number;
}

export interface RoutingNetwork {
  sectors: string[];
  origins: RoutingNode[];
  shelters: RoutingShelter[];
  edges: Array<{
    u: string;
    v: string;
    length_m: number;
    base_risk: number;
    is_underpass: boolean;
    name: string;
  }>;
  chokepoints: Array<{
    id: string;
    edge: [string, string];
    name: string;
  }>;
}

export interface EvacuationCorridor {
  origin_id: string;
  origin_name: string;
  origin_sector: string;
  target_shelter_id: string;
  target_shelter_name: string;
  evacuees_assigned: number;
  distance_km: number;
  duration_min: number;
  srs_score: number;
  route_nodes: string[];
}

export interface ShelterReport {
  shelter_id: string;
  shelter_name: string;
  sector: string;
  capacity: number;
  evacuees_allocated: number;
  occupancy_rate: number;
  safety_rating: number;
}

export interface CityWidePlanResult {
  status: string;
  is_simulated: boolean;
  sector: string;
  total_evacuation_corridors: number;
  total_evacuees_safeguarded: number;
  avg_route_safety_score: number;
  avg_evacuation_distance_km: number;
  avg_evacuation_duration_min: number;
  corridors: EvacuationCorridor[];
  shelters: ShelterReport[];
  prototype_only: boolean;
  network_basis: string;
}

async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const accessToken = sessionStorage.getItem('aquarizz_access_token');
  const response = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
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
  login: async (username: string, password: string) => {
    const form = new URLSearchParams({ username, password });
    const response = await fetch(`${BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: form,
    });
    if (!response.ok) {
      let message = response.statusText;
      try {
        const body = await response.json();
        message = body.detail || body.message || message;
      } catch {
        // Keep the HTTP status text when the response has no JSON body.
      }
      throw new Error(`API Error [${response.status}]: ${message}`);
    }
    return response.json() as Promise<{ access_token: string; token_type: string; username: string; role: string }>;
  },
  // Risk
  fetchRisk: () => fetchApi<WardRisk[]>('/risk'),
  fetchWardRisk: (wardId: string) => fetchApi<WardRisk>(`/risk/${wardId}`),

  // Zones & Geospatial
  fetchZones: () => fetchApi<any>('/zones'),
  fetchZoneById: (wardId: string) => fetchApi<any>(`/zones/${wardId}`),
  fetchHistoricalFloods2015: () => fetchApi<any>('/layers/historical-floods/2015'),
  fetchHistoricalRainfall2015: () => fetchApi<any>('/layers/rainfall/2015'),
  fetchTNSMARTRainfall20261011: () => fetchApi<any>('/layers/rainfall/tnsmart/2026-10-11'),

  // Assessments & Explanation
  fetchAssessments: () => fetchApi<any[]>('/assessments'),
  fetchAssessmentDetail: (id: string) => fetchApi<any>(`/assessments/${id}`),
  triggerAssessment: (wardId: string) =>
    fetchApi<any>('/assessments', { method: 'POST', body: JSON.stringify({ ward_id: wardId }) }),
  fetchExplanation: (assessmentId: string) => fetchApi<any>(`/explanations/${assessmentId}`),

  // Reviews & Approval State Machine
  fetchPendingReviews: (department?: string) =>
    fetchApi<PendingReview[]>(
      department && department !== 'ALL'
        ? `/reviews/pending?department=${encodeURIComponent(department)}`
        : '/reviews/pending'
    ),
  approveReview: (caseId: string, rationale: string, checklist: Record<string, boolean>) =>
    fetchApi<any>(`/reviews/${caseId}/approve`, {
      method: 'POST',
      body: JSON.stringify({ rationale, checklist }),
    }),
  rejectReview: (caseId: string, rationale: string) =>
    fetchApi<any>(`/reviews/${caseId}/reject`, {
      method: 'POST',
      body: JSON.stringify({ rationale }),
    }),

  // Alerts
  fetchAlerts: () => fetchApi<any[]>('/alerts'),
  dispatchAlert: (caseId: string, message?: string) =>
    fetchApi<any>(`/alerts/${caseId}/dispatch`, {
      method: 'POST',
      body: JSON.stringify({ message }),
    }),

  // Routing
  fetchRoutingNetwork: () => fetchApi<RoutingNetwork>('/routes/network'),
  calculateRoute: (origin: string, destination: string, overlay?: Record<string, number>) =>
    fetchApi<RouteResult>('/routes', {
      method: 'POST',
      body: JSON.stringify({
        origin_node: origin,
        destination_node: destination,
        flood_penalty_overlay: overlay,
      }),
    }),
  simulateCityWidePlan: (sector?: string, overlay?: Record<string, number>) =>
    fetchApi<CityWidePlanResult>('/routes/citywide-plan', {
      method: 'POST',
      body: JSON.stringify({
        sector: sector || 'All Chennai',
        flood_penalty_overlay: overlay,
      }),
    }),

  // Demo & Simulation Control
  getDemoState: () => fetchApi<DemoState>('/demo/state'),
  controlDemo: (action: string, step?: number) =>
    fetchApi<any>('/demo/control', {
      method: 'POST',
      body: JSON.stringify({ action, ...(step === undefined ? {} : { step }) }),
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
  dispatchRecommendation: (payload: {
    action_id: string;
    action_title: string;
    action_description: string;
    ward_id: string;
    ward_name?: string;
    zone?: string;
    department: string;
    authority_of_control?: string;
    priority?: string;
    urgency?: string;
  }) =>
    fetchApi<any>('/recommendations/dispatch', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  // Audit Log & Verification
  fetchAuditLog: () => fetchApi<any[]>('/audit'),
  verifyAuditChain: () => fetchApi<any>('/audit/verify', { method: 'POST' }),
};
