import api from './api';

export interface FrameworkProfile {
  id: number;
  projectId: number;
  frameworkType: 'PLAYWRIGHT' | 'SELENIUM';
  repoUrl: string;
  branch: string;
  status: 'PENDING' | 'ANALYSING' | 'CONNECTED' | 'FAILED';
  errorMessage?: string;
  baseClass?: string;
  folderStructure?: string;
  namingConventions?: string;
  importPatterns?: string;
  hookPatterns?: string;
  customUtilities?: string;
  pageObjectsCount?: number;
  testFilesCount?: number;
  summaryText?: string;
  analysedAt?: string;
  createdAt: string;
}

export interface AutomationExecution {
  id: number;
  projectId: number;
  frameworkProfileId?: number;
  suiteName: string;
  frameworkType: 'PLAYWRIGHT' | 'SELENIUM';
  appUrl?: string;
  generatedCode?: string;
  status: 'QUEUED' | 'RUNNING' | 'PASSED' | 'FAILED' | 'ERROR';
  totalTests: number;
  passed: number;
  failed: number;
  skipped: number;
  durationMs?: number;
  triggeredBy?: string;
  reportUrl?: string;
  startedAt?: string;
  completedAt?: string;
  createdAt: string;
}

export interface AutomationResult {
  id: number;
  testName: string;
  testClass?: string;
  status: string;
  durationMs?: number;
  errorMessage?: string;
  screenshotBase64?: string;
  aiExplanation?: string;
  jiraTicketKey?: string;
  jiraTicketUrl?: string;
}

export interface ReportSummary {
  id: number;
  title: string;
  passRate?: number;
  totalTests: number;
  passed: number;
  failed: number;
  shareToken: string;
  executionDate?: string;
  createdAt: string;
}

export const automationApi = {
  // Framework
  getFrameworks: (projectId: number) =>
    api.get<FrameworkProfile[]>(`/automation/projects/${projectId}/frameworks`).then(r => r.data),

  connectFramework: (data: {
    projectId: number;
    frameworkType: string;
    repoUrl: string;
    branch: string;
    githubToken?: string;
  }) => api.post<FrameworkProfile>('/automation/frameworks/connect', data).then(r => r.data),

  // Code generation
  generateCode: (data: {
    projectId: number;
    frameworkProfileId: number;
    suiteName: string;
    testCaseTitles?: string[];
    testCaseDescriptions?: string[];
  }) => api.post<AutomationExecution>('/automation/generate-code', data).then(r => r.data),

  // Execution
  execute: (executionId: number, appUrl?: string) =>
    api.post<AutomationExecution>(`/automation/execute/${executionId}`, null, {
      params: appUrl ? { appUrl } : {},
    }).then(r => r.data),

  getExecutions: (projectId: number) =>
    api.get<AutomationExecution[]>(`/automation/projects/${projectId}/executions`).then(r => r.data),

  getExecution: (id: number) =>
    api.get<AutomationExecution>(`/automation/executions/${id}`).then(r => r.data),

  getResults: (executionId: number) =>
    api.get<AutomationResult[]>(`/automation/executions/${executionId}/results`).then(r => r.data),

  // Reports
  getReports: (projectId: number) =>
    api.get<ReportSummary[]>(`/automation/projects/${projectId}/reports`).then(r => r.data),
};
