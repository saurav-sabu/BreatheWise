import type {
  ChatRequest,
  ChatResponse,
  CommunityFeedResponse,
  CommunityPostCreate,
  CommunityPostOut,
  CommunityPostType,
  CommunitySummaryResponse,
  CurrentAQIResponse,
  ForecastAQIResponse,
  HealthPayload,
  HouseholdProfileCreate,
  HouseholdProfileOut,
  ImpactActionCreate,
  ImpactActionOut,
  ImpactCatalogItem,
  ImpactSummaryResponse,
  IndoorAdvisorRequest,
  IndoorAdvisorResponse,
  LocationSearchResponse,
  RecommendationsRequest,
  RecommendationsResponse,
  RoutinePlanRequest,
  RoutinePlanResponse,
} from '../types/api'

const API_BASE = (import.meta.env.VITE_API_BASE_URL || '/api/v1').replace(/\/$/, '')

export class ApiError extends Error {
  status: number
  detail: string

  constructor(status: number, detail: string) {
    super(detail)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
  })

  if (!response.ok) {
    let detail = `Request failed with HTTP ${response.status}`
    try {
      const errBody = (await response.json()) as { detail?: unknown }
      if (typeof errBody.detail === 'string') {
        detail = errBody.detail
      }
    } catch {
      // Ignore non-JSON error bodies
    }
    throw new ApiError(response.status, detail)
  }

  return (await response.json()) as T
}

export function getHealth(signal?: AbortSignal): Promise<HealthPayload> {
  return requestJson<HealthPayload>('/health', { signal })
}

export function getCurrentAqi(
  params: {
    lat: number
    lon: number
    city: string
    country?: string | null
    demoMode?: boolean
  },
  signal?: AbortSignal,
): Promise<CurrentAQIResponse> {
  const qs = new URLSearchParams({
    lat: String(params.lat),
    lon: String(params.lon),
    city: params.city,
    demo_mode: String(Boolean(params.demoMode)),
  })
  if (params.country) {
    qs.set('country', params.country)
  }
  return requestJson<CurrentAQIResponse>(`/aqi/current?${qs.toString()}`, { signal })
}

export function getForecastAqi(
  params: {
    lat: number
    lon: number
    city: string
    country?: string | null
    hours?: number
    demoMode?: boolean
  },
  signal?: AbortSignal,
): Promise<ForecastAQIResponse> {
  const qs = new URLSearchParams({
    lat: String(params.lat),
    lon: String(params.lon),
    city: params.city,
    hours: String(params.hours ?? 24),
    demo_mode: String(Boolean(params.demoMode)),
  })
  if (params.country) {
    qs.set('country', params.country)
  }
  return requestJson<ForecastAQIResponse>(`/aqi/forecast?${qs.toString()}`, { signal })
}

export function searchLocations(
  query: string,
  limit = 6,
  signal?: AbortSignal,
): Promise<LocationSearchResponse> {
  const qs = new URLSearchParams({ q: query.trim(), limit: String(limit) })
  return requestJson<LocationSearchResponse>(`/aqi/locations/search?${qs.toString()}`, { signal })
}

export function getProfile(profileId: string, signal?: AbortSignal): Promise<HouseholdProfileOut> {
  return requestJson<HouseholdProfileOut>(`/profiles/${encodeURIComponent(profileId)}`, { signal })
}

export function saveProfile(
  payload: HouseholdProfileCreate,
  signal?: AbortSignal,
): Promise<HouseholdProfileOut> {
  return requestJson<HouseholdProfileOut>('/profiles', {
    method: 'POST',
    body: JSON.stringify(payload),
    signal,
  })
}

export function getRecommendations(
  payload: RecommendationsRequest,
  signal?: AbortSignal,
): Promise<RecommendationsResponse> {
  return requestJson<RecommendationsResponse>('/advisor/recommendations', {
    method: 'POST',
    body: JSON.stringify(payload),
    signal,
  })
}

export function assessIndoorAir(
  payload: IndoorAdvisorRequest,
  signal?: AbortSignal,
): Promise<IndoorAdvisorResponse> {
  return requestJson<IndoorAdvisorResponse>('/advisor/indoor', {
    method: 'POST',
    body: JSON.stringify(payload),
    signal,
  })
}

export function getRoutinePlan(
  payload: RoutinePlanRequest,
  signal?: AbortSignal,
): Promise<RoutinePlanResponse> {
  return requestJson<RoutinePlanResponse>('/advisor/routine', {
    method: 'POST',
    body: JSON.stringify(payload),
    signal,
  })
}

export function getImpactCatalog(signal?: AbortSignal): Promise<ImpactCatalogItem[]> {
  return requestJson<ImpactCatalogItem[]>('/impact/catalog', { signal })
}

export function logImpactAction(
  payload: ImpactActionCreate,
  signal?: AbortSignal,
): Promise<ImpactActionOut> {
  return requestJson<ImpactActionOut>('/impact/actions', {
    method: 'POST',
    body: JSON.stringify(payload),
    signal,
  })
}

export function getImpactSummary(
  profileId: string,
  signal?: AbortSignal,
): Promise<ImpactSummaryResponse> {
  return requestJson<ImpactSummaryResponse>(
    `/impact/summary?profile_id=${encodeURIComponent(profileId)}`,
    { signal },
  )
}

export async function deleteImpactAction(actionId: number, signal?: AbortSignal): Promise<void> {
  const response = await fetch(`${API_BASE}/impact/actions/${actionId}`, {
    method: 'DELETE',
    signal,
  })
  if (!response.ok) {
    throw new ApiError(response.status, `Delete failed with HTTP ${response.status}`)
  }
}

export function sendChatMessage(payload: ChatRequest, signal?: AbortSignal): Promise<ChatResponse> {
  return requestJson<ChatResponse>('/chat', {
    method: 'POST',
    body: JSON.stringify(payload),
    signal,
  })
}

export function getCommunityPosts(
  city: string,
  postType?: CommunityPostType | null,
  signal?: AbortSignal,
): Promise<CommunityFeedResponse> {
  const qs = new URLSearchParams({ city })
  if (postType) qs.set('post_type', postType)
  return requestJson<CommunityFeedResponse>(`/community/posts?${qs.toString()}`, { signal })
}

export function getCommunitySummary(
  city: string,
  signal?: AbortSignal,
): Promise<CommunitySummaryResponse> {
  return requestJson<CommunitySummaryResponse>(
    `/community/summary?city=${encodeURIComponent(city)}`,
    { signal },
  )
}

export function createCommunityPost(
  payload: CommunityPostCreate,
  signal?: AbortSignal,
): Promise<CommunityPostOut> {
  return requestJson<CommunityPostOut>('/community/posts', {
    method: 'POST',
    body: JSON.stringify(payload),
    signal,
  })
}

export function upvoteCommunityPost(postId: number, signal?: AbortSignal): Promise<CommunityPostOut> {
  return requestJson<CommunityPostOut>(`/community/posts/${postId}/upvote`, {
    method: 'POST',
    signal,
  })
}

export function reportCommunityPost(
  postId: number,
  reason: 'spam' | 'misinformation' | 'medical_claim' | 'abusive' | 'pii_leak',
  details?: string,
  signal?: AbortSignal,
): Promise<{ post_id: number; report_count: number; moderation_status: string; message: string }> {
  return requestJson(`/community/posts/${postId}/report`, {
    method: 'POST',
    body: JSON.stringify({ reason, details: details || null }),
    signal,
  })
}
