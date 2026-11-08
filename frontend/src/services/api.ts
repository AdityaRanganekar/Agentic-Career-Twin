import axios from 'axios';
import { User, AnalysisResult, HistoricalRun } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
});

export const authService = {
  async login(identifier: string, password: string): Promise<User> {
    const response = await apiClient.post<User>('/auth/login', { identifier, password });
    return response.data;
  },

  async signup(name: string, username: string, email: string, password: string): Promise<User> {
    const response = await apiClient.post<User>('/auth/signup', { name, username, email, password });
    return response.data;
  },

  async getGoogleUrl(): Promise<{ configured: boolean; auth_url: string | null }> {
    const response = await apiClient.get<{ configured: boolean; auth_url: string | null }>('/auth/google-url');
    return response.data;
  },

  async googleAuth(payload: { code?: string; email?: string; name?: string; google_id?: string }): Promise<User> {
    const response = await apiClient.post<User>('/auth/google', payload);
    return response.data;
  },
};

export const assessmentService = {
  async processResume(formData: FormData): Promise<AnalysisResult> {
    const response = await apiClient.post<AnalysisResult>('/process-resume', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
};

export const historyService = {
  async getHistory(studentIdentifier: string | number): Promise<HistoricalRun[]> {
    const response = await apiClient.get<HistoricalRun[]>(`/history/${studentIdentifier}`);
    return response.data;
  },
};

