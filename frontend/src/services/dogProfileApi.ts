/**
 * Dog Profile API Service
 * Connects to the intelligent_chat Dog Profile API
 */

const API_BASE_URL = `${process.env.NEXT_PUBLIC_FASTAPI_BASE_URL}/api/v2`;

// Helper function to get auth token
function getAuthToken(): string | null {
  if (typeof window === 'undefined') return null;
  // Check cookies first (primary auth method)
  const cookieToken = document.cookie.split('; ').find(row => row.startsWith('token='))?.split('=')[1];
  if (cookieToken) return cookieToken;
  // Fallback to localStorage
  return localStorage.getItem('token') || null;
}

// Helper function to get auth headers
function getAuthHeaders(): HeadersInit {
  const token = getAuthToken();
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  return headers;
}

export interface DogProfile {
  id: number;
  user_id: number;
  name: string;
  breed?: string;
  age?: number;
  date_of_birth?: string;
  weight?: number;
  gender?: string;
  color?: string;
  image_url?: string;
  image_description?: string;
  comprehensive_profile?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface DogProfileCreate {
  name: string;
  breed?: string;
  age?: number;
  date_of_birth?: string;
  weight?: number;
  gender?: string;
  color?: string;
  image_url?: string;
  image_description?: string;
  comprehensive_profile?: Record<string, any>;
}

export interface DogProfileUpdate extends Partial<DogProfileCreate> {}

export interface DogProfileListResponse {
  dogs: DogProfile[];
}

export interface ImageUploadRequest {
  image_data: string;
  dog_name: string;
  breed?: string;
  age?: number;
  gender?: string;
  color?: string;
}

export interface ImageUploadResponse {
  image_url: string;
  image_description: string;
}

export interface VetReportUploadRequest {
  dog_id: number;
  file_data: string;
  filename: string;
  content_type: string;
}

export interface VetReportUploadResponse {
  s3_url: string;
  status: string;
  document_id: number;
}

/**
 * Get all dog profiles for the current user
 */
export async function listDogProfiles(): Promise<DogProfileListResponse> {
  const response = await fetch(`${API_BASE_URL}/dogs`, {
    headers: getAuthHeaders(),
    credentials: 'include',
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch dog profiles: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Get a specific dog profile by ID
 */
export async function getDogProfile(dogId: number): Promise<DogProfile> {
  const response = await fetch(`${API_BASE_URL}/dogs/${dogId}`, {
    headers: getAuthHeaders(),
    credentials: 'include',
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch dog profile: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Create a new dog profile
 */
export async function createDogProfile(dogData: DogProfileCreate): Promise<DogProfile> {
  const response = await fetch(`${API_BASE_URL}/dogs`, {
    method: 'POST',
    headers: getAuthHeaders(),
    credentials: 'include',
    body: JSON.stringify(dogData),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    const errorMessage = typeof error.detail === 'object' 
      ? JSON.stringify(error.detail) 
      : (error.detail || response.statusText);
    throw new Error(`Failed to create dog profile: ${errorMessage}`);
  }

  return response.json();
}

/**
 * Update a dog profile
 */
export async function updateDogProfile(dogId: number, dogData: DogProfileUpdate): Promise<DogProfile> {
  const response = await fetch(`${API_BASE_URL}/dogs/${dogId}`, {
    method: 'PUT',
    headers: getAuthHeaders(),
    credentials: 'include',
    body: JSON.stringify(dogData),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(`Failed to update dog profile: ${error.detail || response.statusText}`);
  }

  return response.json();
}

/**
 * Delete a dog profile
 */
export async function deleteDogProfile(dogId: number): Promise<{ success: boolean; message: string }> {
  const response = await fetch(`${API_BASE_URL}/dogs/${dogId}`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
    credentials: 'include',
  });

  if (!response.ok) {
    throw new Error(`Failed to delete dog profile: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Upload dog image and get Claude Vision description
 */
export async function uploadDogImage(request: ImageUploadRequest): Promise<ImageUploadResponse> {
  const response = await fetch(`${API_BASE_URL}/dogs/upload-image`, {
    method: 'POST',
    headers: getAuthHeaders(),
    credentials: 'include',
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(`Failed to upload image: ${error.detail || response.statusText}`);
  }

  return response.json();
}

/**
 * Upload vet report for a dog profile
 */
export async function uploadVetReport(request: VetReportUploadRequest): Promise<VetReportUploadResponse> {
  const response = await fetch(`${API_BASE_URL}/dogs/upload-vet-report`, {
    method: 'POST',
    headers: getAuthHeaders(),
    credentials: 'include',
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(`Failed to upload vet report: ${error.detail || response.statusText}`);
  }

  return response.json();
}
