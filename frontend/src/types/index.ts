export type UserRole = 'ADMIN' | 'QA_LEAD' | 'QA_ENGINEER' | 'VIEWER';
export type TestRunStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED';
export type DefectSeverity = 'P0' | 'P1' | 'P2' | 'P3';
export type DefectStatus = 'OPEN' | 'IN_PROGRESS' | 'RESOLVED' | 'WONT_FIX';
export type McpServerType = 'PLAYWRIGHT' | 'GITHUB' | 'FILESYSTEM' | 'JIRA' | 'SLACK';

export interface User {
  id: number;
  email: string;
  role: UserRole;
  name?: string;
}

export interface AuthResponse {
  accessToken: string;
  refreshToken: string;
  email: string;
  role: UserRole;
  name?: string;
}

export interface Project {
  id: number;
  name: string;
  repoUrl?: string;
  techStack?: string;
  status?: string;
  githubToken?: string;
  createdAt: string;
  activeTestRun: boolean;
}

export interface TestRun {
  id: number;
  projectId: number;
  status: TestRunStatus;
  triggeredBy: string;
  startedAt: string;
  completedAt?: string;
  defectCount: number;
  riskScore?: number;
}

export interface Defect {
  id: number;
  testRunId: number;
  severity: DefectSeverity;
  title: string;
  description: string;
  aiExplanation: string;
  consistencyScore: number;
  jiraTicketId?: string;
  status: DefectStatus;
  createdAt: string;
}

export interface RiskScore {
  id: number;
  projectId: number;
  filePath: string;
  riskScore: number;
  anomalyFlag: boolean;
  commitSha: string;
  scoredAt: string;
}

export interface McpStatus {
  serverType: McpServerType;
  isActive: boolean;
  lastChecked: string;
  config?: Record<string, string>;
}

export interface DashboardStats {
  totalProjects: number;
  activeTestRuns: number;
  openDefects: number;
  avgRiskScore: number;
}
