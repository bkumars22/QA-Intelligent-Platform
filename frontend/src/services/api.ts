import axios from 'axios';
import type {
  AuthResponse,
  Project,
  TestRun,
  Defect,
  DefectStatus,
  RiskScore,
  McpStatus,
  DashboardStats,
  McpServerType,
} from '../types';
import {
  DEMO_TOKEN,
  mockProjects,
  mockTestRuns,
  mockDefects,
  mockRiskScores,
  mockMcpStatus,
  mockDashboardStats,
  getAllMockDefects,
  getMockTestRun,
  getMockDefect,
} from './mockData';

// Module-level token store — NOT localStorage
let _token: string | null = null;

export function setToken(t: string): void {
  _token = t;
}

export function clearToken(): void {
  _token = null;
}

export function getToken(): string {
  return _token ?? '';
}

function isDemo(): boolean {
  return _token === DEMO_TOKEN;
}

export function isDemoMode(): boolean {
  return _token === DEMO_TOKEN;
}

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? '/api',
  headers: { 'Content-Type': 'application/json' },
});

// Request interceptor: attach Bearer token
api.interceptors.request.use((config) => {
  if (_token) {
    config.headers.Authorization = `Bearer ${_token}`;
  }
  return config;
});

// Response interceptor: handle 401
api.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    if (
      axios.isAxiosError(error) &&
      error.response?.status === 401
    ) {
      clearToken();
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth
export async function login(email: string, password: string): Promise<AuthResponse> {
  const { data } = await api.post<AuthResponse>('/auth/login', { email, password });
  return data;
}

// Projects
export async function getProjects(): Promise<Project[]> {
  if (isDemo()) return Promise.resolve(mockProjects);
  const { data } = await api.get<Project[]>('/projects');
  return data;
}

export async function createProject(payload: {
  name: string;
  repoUrl: string;
  githubToken: string;
}): Promise<Project> {
  if (isDemo()) {
    return Promise.reject(new Error('Project creation is disabled in demo mode'));
  }
  const { data } = await api.post<Project>('/projects', payload);
  return data;
}

export async function deleteProject(id: number): Promise<void> {
  if (isDemo()) return Promise.reject(new Error('Delete is disabled in demo mode'));
  await api.delete(`/projects/${id}`);
}

export async function connectRepo(id: number, token: string): Promise<void> {
  if (isDemo()) return Promise.resolve();
  await api.post(`/projects/${id}/connect-repo`, { token });
}

export async function triggerAnalysis(id: number): Promise<{ runId: number }> {
  if (isDemo()) {
    const proj = mockProjects.find(p => p.id === id);
    if (proj) proj.activeTestRun = true;

    await new Promise(r => setTimeout(r, 3000));

    const runId = Date.now();
    const defectCount = Math.floor(Math.random() * 4);
    const newRun: TestRun = {
      id: runId,
      projectId: id,
      status: 'COMPLETED',
      triggeredBy: 'demo@qaip.io',
      startedAt: new Date(Date.now() - 3100).toISOString(),
      completedAt: new Date().toISOString(),
      defectCount,
      riskScore: Math.round((Math.random() * 0.45 + 0.2) * 1000) / 1000,
    };
    if (!mockTestRuns[id]) mockTestRuns[id] = [];
    mockTestRuns[id].unshift(newRun);

    if (proj) proj.activeTestRun = false;
    return { runId };
  }
  const { data } = await api.post<{ runId: number }>(`/projects/${id}/analyze`);
  return data;
}

// Test Runs
export async function getTestRuns(projectId: number): Promise<TestRun[]> {
  if (isDemo()) return Promise.resolve(mockTestRuns[projectId] ?? []);
  const { data } = await api.get<TestRun[]>(`/projects/${projectId}/test-runs`);
  return data;
}

export async function getTestRun(id: number): Promise<TestRun> {
  if (isDemo()) {
    const run = getMockTestRun(id);
    if (run) return Promise.resolve(run);
    return Promise.reject(new Error('Test run not found'));
  }
  const { data } = await api.get<TestRun>(`/test-runs/${id}`);
  return data;
}

// Defects
export async function getDefects(runId: number): Promise<Defect[]> {
  if (isDemo()) return Promise.resolve(mockDefects[runId] ?? []);
  const { data } = await api.get<Defect[]>(`/test-runs/${runId}/defects`);
  return data;
}

export async function getDefect(id: number): Promise<Defect> {
  if (isDemo()) {
    const defect = getMockDefect(id);
    if (defect) return Promise.resolve(defect);
    return Promise.reject(new Error('Defect not found'));
  }
  const { data } = await api.get<Defect>(`/defects/${id}`);
  return data;
}

export async function updateDefectStatus(id: number, status: DefectStatus): Promise<Defect> {
  if (isDemo()) {
    const defect = getMockDefect(id);
    if (defect) {
      defect.status = status;
      return Promise.resolve(defect);
    }
    return Promise.reject(new Error('Defect not found'));
  }
  const { data } = await api.patch<Defect>(`/defects/${id}/status`, { status });
  return data;
}

// Risk Scores
export async function getRiskScores(projectId: number): Promise<RiskScore[]> {
  if (isDemo()) return Promise.resolve(mockRiskScores[projectId] ?? []);
  const { data } = await api.get<RiskScore[]>(`/projects/${projectId}/risk-scores`);
  return data;
}

// MCP
export async function getMcpStatus(projectId: number): Promise<McpStatus[]> {
  if (isDemo()) return Promise.resolve(mockMcpStatus[projectId] ?? []);
  const { data } = await api.get<McpStatus[]>(`/projects/${projectId}/mcp-status`);
  return data;
}

export async function configureMcp(
  projectId: number,
  payload: { serverType: McpServerType; config: Record<string, string> }
): Promise<void> {
  if (isDemo()) return Promise.resolve();
  await api.post(`/projects/${projectId}/mcp-config`, payload);
}

// Dashboard
export async function getDashboardStats(): Promise<DashboardStats> {
  if (isDemo()) return Promise.resolve(mockDashboardStats);
  const { data } = await api.get<DashboardStats>('/dashboard/stats');
  return data;
}

export async function getRiskHeatmap(projectId: number): Promise<RiskScore[]> {
  if (isDemo()) return Promise.resolve(mockRiskScores[projectId] ?? []);
  const { data } = await api.get<RiskScore[]>(`/projects/${projectId}/risk-heatmap`);
  return data;
}

// All defects (used by defects list page)
export async function getAllDefects(): Promise<Defect[]> {
  if (isDemo()) return Promise.resolve(getAllMockDefects());
  const { data } = await api.get<Defect[]>('/defects');
  return data;
}

export default api;
