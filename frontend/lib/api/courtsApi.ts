/**
 * Courts API Layer
 * 
 * This is the NETWORK BOUNDARY - all fetch errors get:
 * 1. Transformed into typed exceptions
 * 2. Logged with correlation IDs
 * 
 * UI components catch these exceptions and display user-friendly messages.
 */

import { NetworkError, APIError, RateLimitError, parseAPIError } from './exceptions';

// Types
export interface Court {
  id: number;
  name: string | null;
  type: string;
  lat: number;
  lng: number;
  surface: string;
  is_public: boolean | null;
  school: boolean;
  cluster_group_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface SearchFilters {
  bbox: [number, number, number, number];
  zoom: number;
  sport?: string;
  surface_type?: string;
  is_public?: boolean;
}

export interface CourtsMetadata {
  sports: string[];
  surfaceTypes: string[];
}

export interface CoverageArea {
  id: number;
  name: string;
  region: string;
  boundary: {
    type: 'Polygon';
    coordinates: number[][][];
  };
  court_count: number;
  last_updated: string;
  created_at: string;
}

// API configuration
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001';

/**
 * Search courts within a viewport
 * Sentry handles distributed tracing via sentry-trace/baggage headers automatically
 */
export async function searchCourts(filters: SearchFilters): Promise<Court[]> {
  try {
    const queryParams = new URLSearchParams({
      zoom: filters.zoom.toString(),
      bbox: filters.bbox.join(',')
    });

    if (filters.sport) queryParams.set('sport', filters.sport);
    if (filters.surface_type) queryParams.set('surface_type', filters.surface_type);
    if (filters.is_public !== undefined) queryParams.set('is_public', String(filters.is_public));

    const response = await fetch(`${API_URL}/api/courts/search?${queryParams.toString()}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      },
      mode: 'cors',
      credentials: 'omit'
    });

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      const retryAfter = response.headers.get('Retry-After') || undefined;
      throw parseAPIError(response.status, data, retryAfter);
    }

    const result = await response.json();
    
    if (!result.success || !Array.isArray(result.data)) {
      throw new APIError(result.error || 'Invalid response format', result.code || 'INVALID_RESPONSE', 500);
    }

    return result.data;
    
  } catch (error) {
    // Re-throw API errors as-is
    if (error instanceof APIError) {
      throw error;
    }

    // Transform network errors (offline, timeout, DNS failure)
    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new NetworkError('Unable to connect to server. Please check your internet connection.');
    }

    // Unknown errors
    console.error('Unexpected error in searchCourts:', error);
    throw new NetworkError('An unexpected error occurred while searching courts');
  }
}

/**
 * Get court by ID
 */
export async function getCourtById(id: number): Promise<Court> {
  try {
    const response = await fetch(`${API_URL}/api/courts/${id}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      }
    });

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw parseAPIError(response.status, data);
    }

    const result = await response.json();
    
    if (!result.success || !result.data) {
      throw new APIError(result.error || 'Invalid response format', result.code || 'INVALID_RESPONSE', 500);
    }

    return result.data;
    
  } catch (error) {
    if (error instanceof APIError) throw error;
    if (error instanceof TypeError) {
      throw new NetworkError('Unable to connect to server.');
    }
    throw new NetworkError('An unexpected error occurred');
  }
}

/**
 * Update court
 */
export async function updateCourt(
  id: number, 
  data: Partial<Court> & { cluster_fields?: { cluster_group_name?: string | null } }
): Promise<Court> {
  try {
    const response = await fetch(`${API_URL}/api/courts/${id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(data)
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw parseAPIError(response.status, errorData);
    }

    const result = await response.json();
    
    if (!result.success || !result.data) {
      throw new APIError(result.error || 'Invalid response format', result.code || 'INVALID_RESPONSE', 500);
    }

    return result.data;
    
  } catch (error) {
    if (error instanceof APIError) throw error;
    if (error instanceof TypeError) {
      throw new NetworkError('Unable to connect to server.');
    }
    throw new NetworkError('An unexpected error occurred while updating court');
  }
}

/**
 * Get courts metadata (available sports and surface types)
 */
export async function getMetadata(): Promise<CourtsMetadata> {
  try {
    const response = await fetch(`${API_URL}/api/courts/metadata`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      }
    });

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw parseAPIError(response.status, data);
    }

    const result = await response.json();
    
    if (!result.success || !result.data) {
      throw new APIError(result.error || 'Invalid response format', result.code || 'INVALID_RESPONSE', 500);
    }

    return result.data;
    
  } catch (error) {
    if (error instanceof APIError) throw error;
    if (error instanceof TypeError) {
      throw new NetworkError('Unable to connect to server.');
    }
    throw new NetworkError('An unexpected error occurred while fetching metadata');
  }
}

/**
 * Get coverage areas (regions where court data is available)
 */
export async function getCoverageAreas(region?: string): Promise<CoverageArea[]> {
  try {
    const url = region
      ? `${API_URL}/api/courts/coverage?region=${encodeURIComponent(region)}`
      : `${API_URL}/api/courts/coverage`;

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      },
      mode: 'cors',
      credentials: 'omit'
    });

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw parseAPIError(response.status, data);
    }

    const result = await response.json();

    if (!result.success || !Array.isArray(result.data)) {
      throw new APIError(result.error || 'Invalid response format', result.code || 'INVALID_RESPONSE', 500);
    }

    return result.data;

  } catch (error) {
    if (error instanceof APIError) throw error;
    if (error instanceof TypeError) {
      throw new NetworkError('Unable to connect to server.');
    }
    throw new NetworkError('An unexpected error occurred while fetching coverage areas');
  }
}

// Re-export exceptions for UI components
export { NetworkError, APIError, RateLimitError } from './exceptions';

