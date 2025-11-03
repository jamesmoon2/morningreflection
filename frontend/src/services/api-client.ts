/**
 * API client for Morning Reflection backend
 *
 * Handles all HTTP communication with the API Gateway backend.
 * Automatically includes authentication tokens and handles errors.
 */

import axios, { AxiosInstance, AxiosError } from 'axios';
import { ApiError, ApiResponse } from '../types';

class ApiClient {
  private client: AxiosInstance;
  private tokenGetter: (() => Promise<string | null>) | null = null;

  constructor(baseURL: string) {
    this.client = axios.create({
      baseURL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor to add auth token
    this.client.interceptors.request.use(
      async (config) => {
        if (this.tokenGetter) {
          const token = await this.tokenGetter();
          if (token) {
            config.headers.Authorization = `Bearer ${token}`;
          }
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError<ApiError>) => {
        const apiError: ApiError = {
          statusCode: error.response?.status || 500,
          error: error.response?.data?.error || 'Unknown error',
          message: error.response?.data?.message || error.message || 'An error occurred',
        };
        return Promise.reject(apiError);
      }
    );
  }

  /**
   * Set the function to retrieve auth tokens
   */
  setTokenGetter(getter: () => Promise<string | null>): void {
    this.tokenGetter = getter;
  }

  /**
   * Generic GET request
   */
  async get<T>(path: string, params?: Record<string, unknown>): Promise<T> {
    const response = await this.client.get<T>(path, { params });
    return response.data;
  }

  /**
   * Generic POST request
   */
  async post<T>(path: string, data?: unknown): Promise<T> {
    const response = await this.client.post<T>(path, data);
    return response.data;
  }

  /**
   * Generic PUT request
   */
  async put<T>(path: string, data?: unknown): Promise<T> {
    const response = await this.client.put<T>(path, data);
    return response.data;
  }

  /**
   * Generic DELETE request
   */
  async delete<T>(path: string): Promise<T> {
    const response = await this.client.delete<T>(path);
    return response.data;
  }
}

// Create singleton instance
const apiBaseUrl = import.meta.env.VITE_API_URL || '';
export const apiClient = new ApiClient(apiBaseUrl);

/**
 * Helper function to wrap API responses in a standard format
 */
export function wrapApiResponse<T>(data: T): ApiResponse<T> {
  return {
    success: true,
    data,
  };
}

/**
 * Helper function to create error responses
 */
export function createErrorResponse(error: ApiError | Error): ApiResponse<never> {
  if ('statusCode' in error) {
    return {
      success: false,
      error: error.message,
    };
  }
  return {
    success: false,
    error: error.message || 'An unknown error occurred',
  };
}
