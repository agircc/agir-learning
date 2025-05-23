/* eslint-disable @typescript-eslint/no-explicit-any */
/**
 * API client for the AGIR API
 */

// API base URL
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Get JWT token from localStorage
 */
function getAuthToken(): string | null {
  if (typeof window === 'undefined') return null;
  
  try {
    const userData = localStorage.getItem('user');
    if (!userData) return null;
    
    const user = JSON.parse(userData);
    return user.token || null;
  } catch (e) {
    console.error('Failed to parse user data from localStorage', e);
    return null;
  }
}

/**
 * Generic fetch wrapper with error handling
 */
async function fetchAPI<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const token = getAuthToken();
  
  try {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };
    
    // Add Authorization header if token exists
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      // Parse error response
      let errorData;
      try {
        errorData = await response.json();
      } catch {
        errorData = { detail: response.statusText };
      }
      
      throw new Error(
        errorData.detail || `API request failed with status ${response.status}`
      );
    }

    // Return empty object for 204 No Content
    if (response.status === 204) {
      return {} as T;
    }

    return await response.json() as T;
  } catch (error) {
    console.error('API request failed:', error);
    throw error;
  }
}

/**
 * Authentication API
 */
export const authAPI = {
  sendVerificationCode: (email: string) => 
    fetchAPI<{ message: string }>('/api/auth/send-code', {
      method: 'POST',
      body: JSON.stringify({ email }),
    }),
  verifyCode: (email: string, code: string) => 
    fetchAPI<any>('/api/auth/verify', {
      method: 'POST',
      body: JSON.stringify({ email, code }),
    }),
  validateToken: (token: string) =>
    fetchAPI<{ valid: boolean; user_id?: string; error?: string }>('/api/auth/validate-token', {
      method: 'POST',
      body: JSON.stringify({ token }),
    }),
};

/**
 * Scenarios API
 */
export const scenariosAPI = {
  getAll: () => fetchAPI<any[]>('/api/scenarios'),
  getById: (id: string) => fetchAPI<any>(`/api/scenarios/${id}`),
  getEpisodes: (id: string) => fetchAPI<any[]>(`/api/scenarios/${id}/episodes`),
};

/**
 * Episodes API
 */
export const episodesAPI = {
  getAll: () => fetchAPI<any[]>('/api/episodes'),
  getById: (id: string) => fetchAPI<any>(`/api/episodes/${id}`),
  getSteps: (id: string) => fetchAPI<any[]>(`/api/episodes/${id}/steps`),
};

/**
 * Steps API
 */
export const stepsAPI = {
  getAll: () => fetchAPI<any[]>('/api/steps'),
  getById: (id: string) => fetchAPI<any>(`/api/steps/${id}`),
  getDetails: (id: string) => fetchAPI<any>(`/api/steps/${id}/details`),
  getConversations: (id: string) => fetchAPI<any[]>(`/api/steps/${id}/conversations`),
};

/**
 * Users API
 */
export const usersAPI = {
  getAll: () => fetchAPI<any[]>('/api/users'),
  getById: (id: string) => fetchAPI<any>(`/api/users/${id}`),
  getProfile: (id: string) => fetchAPI<any>(`/api/users/${id}/profile`),
};

/**
 * Memories API
 */
export const memoriesAPI = {
  getByUserId: (userId: string, page = 1, pageSize = 10, memoryType?: string, minImportance?: number) => {
    let url = `/api/memories/${userId}?page=${page}&page_size=${pageSize}`;
    if (memoryType) url += `&memory_type=${memoryType}`;
    if (minImportance !== undefined) url += `&min_importance=${minImportance}`;
    return fetchAPI<any>(url);
  },
  getById: (id: string) => fetchAPI<any>(`/api/memories/memory/${id}`),
  getTypes: () => fetchAPI<string[]>('/api/memories/types'),
};

/**
 * Chat API
 */
export const chatAPI = {
  getConversations: () => fetchAPI<any[]>('/api/chat/conversations'),
  getConversationById: (id: string) => fetchAPI<any>(`/api/chat/conversations/${id}`),
  sendToUser: (userId: string, content: string, conversationId?: string) => 
    fetchAPI<any>(`/api/chat/user/${userId}/send`, {
      method: 'POST',
      body: JSON.stringify({ content, conversation_id: conversationId }),
    }),
}; 