export type DataProvenance = 'measured' | 'modeled_current' | 'forecast' | 'demo'

export type AqiStandard = 'CPCB_NAQI' | 'US_EPA_AQI'

export interface HealthPayload {
  status: string
  app_name: string
  environment: string
  version: string
  timestamp: string
  gemini_configured: boolean
  cpcb_configured: boolean
}

export interface LocationOption {
  name: string
  country: string
  country_code?: string | null
  admin1?: string | null
  latitude: number
  longitude: number
  timezone?: string | null
  population?: number | null
}

export interface LocationSearchResponse {
  query: string
  count: number
  source_name: string
  cached: boolean
  results: LocationOption[]
}

export interface NormalizedPollutants {
  pm2_5_ug_m3: number | null
  pm10_ug_m3: number | null
  no2_ug_m3: number | null
  so2_ug_m3: number | null
  o3_ug_m3: number | null
  co_ug_m3: number | null
  co_mg_m3: number | null
  co_ppm: number | null
  no2_ppb: number | null
  so2_ppb: number | null
  o3_ppm: number | null
}

export interface IndexResult {
  standard: AqiStandard
  aqi: number | null
  category: string
  dominant_pollutant: string | null
  sub_indices: Record<string, number>
  meets_minimum_criteria: boolean
  averaging_basis: string
  notes?: string | null
}

export interface CurrentAQIResponse {
  location_name: string
  country?: string | null
  latitude: number
  longitude: number
  provenance: DataProvenance
  source_name: string
  station_name?: string | null
  observed_at: string
  disclaimer: string
  cached: boolean
  pollutants: NormalizedPollutants
  indian_naqi: IndexResult
  us_epa_aqi: IndexResult
}

export interface HourlyForecastItem {
  timestamp: string
  provenance: 'forecast' | 'demo'
  pollutants: NormalizedPollutants
  indian_naqi: IndexResult
  us_epa_aqi: IndexResult
}

export interface ForecastAQIResponse {
  location_name: string
  country?: string | null
  latitude: number
  longitude: number
  provenance: 'forecast' | 'demo'
  source_name: string
  generated_at: string
  hours_requested: number
  hours_returned: number
  disclaimer: string
  cached: boolean
  hourly: HourlyForecastItem[]
}

export type CommuteMode = 'car' | 'two_wheeler' | 'metro' | 'bus' | 'cycle_walk' | 'wfh'
export type HomeType = 'apartment' | 'independent_house' | 'high_rise' | 'shared_housing'
export type CookingFuel = 'lpg' | 'png_piped' | 'induction' | 'electric' | 'biomass'
export type BudgetTier = 'zero_cost' | 'low' | 'moderate' | 'flexible'

export interface HouseholdProfileCreate {
  id?: string | null
  name: string
  city: string
  country: string
  latitude: number
  longitude: number
  household_size: number
  has_children: boolean
  has_seniors: boolean
  respiratory_conditions: string[]
  commute_mode: CommuteMode
  home_type: HomeType
  has_hepa_purifier: boolean
  cooking_fuel: CookingFuel
  budget_tier: BudgetTier
}

export interface HouseholdProfileOut extends HouseholdProfileCreate {
  id: string
  created_at: string
  updated_at: string
}

export type RetrievalMode = 'dense' | 'bm25' | 'hybrid'
export type BenefitType = 'exposure_reduction' | 'emissions_reduction' | 'both'

export interface Citation {
  doc_id: string
  chunk_id: string
  title: string
  source_org: string
  source_url?: string | null
  doc_version: string
  category: string
  excerpt: string
  relevance_score: number
}

export interface ObservabilitySummary {
  llm_latency_ms: number
  embedding_latency_ms: number
  retrieval_latency_ms: number
  total_latency_ms: number
  token_usage: Record<string, number>
  provider_errors: string[]
  fallback_activated: boolean
  embedding_provider: string
  retrieval_mode_used: string
  generation_mode: 'gemini_live' | 'deterministic_fallback'
  nodes_executed: string[]
}

export interface RecommendationItem {
  title: string
  priority: 'urgent' | 'high' | 'medium' | 'low'
  explanation: string
  supporting_evidence: string
  expected_benefit: string
  benefit_type: BenefitType
  effort_level: 'minimal' | 'low' | 'moderate' | 'high'
  estimated_cost: 'free' | 'low_cost' | 'moderate' | 'investment'
  confidence: 'high' | 'medium' | 'low'
  limitations: string
  citation_doc_ids: string[]
}

export interface TransportSwapEstimate {
  from_mode?: string
  to_mode?: string
  distance_km_per_day?: number
  days_per_week?: number
  co2e_kg_avoided_per_week?: number
  pm25_g_avoided_per_week?: number
  co2e_kg_avoided_per_month?: number
  pm25_g_avoided_per_month?: number
  assumptions?: string[]
  distinction_note?: string
}

export interface RecommendationsRequest {
  city: string
  country?: string | null
  latitude: number
  longitude: number
  profile_id?: string | null
  commute_distance_km?: number
  retrieval_mode?: RetrievalMode
  top_k?: number
  demo_mode?: boolean
}

export interface RecommendationsResponse {
  city: string
  aqi_provenance: DataProvenance
  indian_naqi: IndexResult
  us_epa_aqi: IndexResult
  risk_tier: 'low' | 'moderate' | 'high' | 'severe'
  grap_stage_reference?: string | null
  summary: string
  recommendations: RecommendationItem[]
  transport_swap_estimate: TransportSwapEstimate
  citations: Citation[]
  observability: ObservabilitySummary
  medical_disclaimer: string
}

export interface IndoorAdvisorRequest {
  city: string
  country?: string | null
  latitude: number
  longitude: number
  room_area_sqft: number
  ceiling_height_ft: number
  occupants: number
  has_sensitive_occupants: boolean
  cooking_fuel: CookingFuel
  has_exhaust_hood: boolean
  has_hepa_purifier: boolean
  current_purifier_cadr_m3h?: number | null
  window_sealing_quality: 'leaky' | 'average' | 'well_sealed'
  burns_incense_or_candles: boolean
  demo_mode?: boolean
}

export interface IndoorAdvisorResponse {
  city: string
  aqi_provenance: DataProvenance
  indian_naqi: IndexResult
  us_epa_aqi: IndexResult
  room_volume_ft3: number
  room_volume_m3: number
  target_ach: number
  recommended_cadr_m3h: number
  recommended_cadr_cfm: number
  current_achieved_ach?: number | null
  cadr_adequacy_ratio?: number | null
  indoor_risk_score: number
  indoor_risk_level: 'Low' | 'Moderate' | 'Elevated' | 'High'
  safe_ventilation_windows: string[]
  scope_clarification: string
  assumptions: string[]
  guidance_items: RecommendationItem[]
  citations: Citation[]
  observability: ObservabilitySummary
}

export interface RoutineSlot {
  time_window: string
  activity: string
  setting:
    | 'indoor_filtered'
    | 'indoor_cooking_vented'
    | 'transit_low_emission'
    | 'outdoor_masked'
    | 'outdoor_cautious'
  forecast_indian_naqi: number | null
  forecast_us_epa_aqi: number | null
  forecast_pm25_ug_m3: number | null
  guidance: string
  low_emission_swap?: string | null
  exposure_explanation: string
  confidence_note: string
}

export interface RoutinePlanRequest {
  city: string
  country?: string | null
  latitude: number
  longitude: number
  profile_id?: string | null
  work_mode: 'office' | 'hybrid' | 'wfh'
  commute_mode: string
  commute_distance_km: number
  has_children: boolean
  has_seniors: boolean
  demo_mode?: boolean
}

export interface RoutinePlanResponse {
  city: string
  aqi_provenance: DataProvenance
  forecast_provenance: 'forecast' | 'demo'
  current_indian_naqi: IndexResult
  current_us_epa_aqi: IndexResult
  lowest_forecast_window: string
  peak_smog_window: string
  headline: string
  forecast_caveat: string
  slots: RoutineSlot[]
  commute_swap_summary: TransportSwapEstimate
  citations: Citation[]
}

export interface ImpactCatalogItem {
  action_key: string
  label: string
  category: 'mobility' | 'home_energy' | 'clean_air_habit'
  impact_type: 'emissions_and_exposure' | 'emissions_reduction' | 'exposure_reduction'
  unit: string
  co2e_kg_per_unit: number
  pm25_g_per_unit: number
  exposure_hours_saved_per_unit: number
  methodology_note: string
}

export interface ImpactActionCreate {
  profile_id: string
  action_key: string
  quantity: number
  notes?: string | null
}

export interface ImpactActionOut {
  id: number
  profile_id: string
  action_key: string
  action_label: string
  category: string
  quantity: number
  unit: string
  co2e_kg_avoided: number
  pm25_g_avoided: number
  exposure_hours_saved: number
  assumptions_note: string
  notes?: string | null
  logged_at: string
}

export interface ImpactPeriodTotals {
  actions_count: number
  co2e_kg_avoided: number
  pm25_g_avoided: number
  exposure_hours_saved: number
}

export interface DailyImpactPoint {
  date_label: string
  co2e_kg_avoided: number
  pm25_g_avoided: number
  exposure_hours_saved: number
  actions_count: number
}

export interface ImpactSummaryResponse {
  profile_id: string
  daily: ImpactPeriodTotals
  weekly: ImpactPeriodTotals
  monthly: ImpactPeriodTotals
  all_time: ImpactPeriodTotals
  daily_series: DailyImpactPoint[]
  recent_logs: ImpactActionOut[]
  methodology_assumptions: string[]
  distinction_note: string
}

export interface ChatHistoryItem {
  role: 'user' | 'assistant'
  content: string
}

export interface ChatRequest {
  message: string
  thread_id?: string | null
  city: string
  country?: string | null
  latitude: number
  longitude: number
  profile_id?: string | null
  history?: ChatHistoryItem[]
  retrieval_mode?: RetrievalMode
  top_k?: number
  demo_mode?: boolean
}

export interface ChatResponse {
  thread_id: string
  answer: string
  city: string
  aqi_provenance: DataProvenance
  indian_naqi: IndexResult
  us_epa_aqi: IndexResult
  citations: Citation[]
  suggested_followups: string[]
  observability: ObservabilitySummary
  medical_disclaimer: string
}

export type CommunityPostType = 'observation' | 'tip' | 'pledge'
export type ReportReason = 'spam' | 'misinformation' | 'medical_claim' | 'abusive' | 'pii_leak'

export interface CommunityPostCreate {
  city: string
  neighborhood: string
  author_alias: string
  post_type: CommunityPostType
  title: string
  body: string
  action_tag?: string | null
}

export interface CommunityPostOut {
  id: number
  city: string
  neighborhood: string
  author_alias: string
  post_type: CommunityPostType
  title: string
  body: string
  action_tag?: string | null
  upvotes: number
  report_count: number
  moderation_status: 'published' | 'flagged' | 'hidden'
  created_at: string
}

export interface CommunityFeedResponse {
  city: string
  data_classification: 'user_contributed_unverified'
  disclaimer: string
  count: number
  posts: CommunityPostOut[]
}

export interface CommunitySummaryResponse {
  city: string
  data_classification: 'user_contributed_unverified'
  total_published_posts: number
  observations_count: number
  tips_count: number
  pledges_count: number
  total_upvotes: number
  flagged_or_hidden_count: number
  top_action_tags: Array<{ tag: string; count: number }>
  disclaimer: string
}
