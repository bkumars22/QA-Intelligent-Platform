import api from './api';
import { getToken } from './api';
import {
  DEMO_TOKEN,
  mockFrameworks,
  mockExecutions,
  mockResults,
  getMockExecution,
  mockFileTrees,
  mockFileContents,
} from './mockData';

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

export interface FileNode {
  name: string;
  path: string;
  type: 'file' | 'dir';
  sha?: string;
  parent?: string;
}

export interface FileContent {
  path: string;
  content: string;
  sha: string;
}

export interface FileSaveResult {
  committed: boolean;
  sha: string;
  message: string;
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

function isDemo(): boolean {
  return getToken() === DEMO_TOKEN;
}

export const automationApi = {
  getFrameworks: (projectId: number): Promise<FrameworkProfile[]> => {
    if (isDemo()) return Promise.resolve(mockFrameworks[projectId] ?? []);
    return api.get<FrameworkProfile[]>(`/automation/projects/${projectId}/frameworks`).then(r => r.data);
  },

  connectFramework: (data: {
    projectId: number;
    frameworkType: string;
    repoUrl: string;
    branch: string;
    githubToken?: string;
  }): Promise<FrameworkProfile> => {
    if (isDemo()) {
      const profile: FrameworkProfile = {
        id: Date.now(),
        projectId: data.projectId,
        frameworkType: data.frameworkType as 'PLAYWRIGHT' | 'SELENIUM',
        repoUrl: data.repoUrl,
        branch: data.branch,
        status: 'CONNECTED',
        pageObjectsCount: 5,
        testFilesCount: 8,
        summaryText: `${data.frameworkType === 'PLAYWRIGHT' ? 'Playwright TypeScript' : 'Selenium Java'} framework connected from ${data.repoUrl}. QAIP analysed the repo structure and is ready to generate matching tests.`,
        analysedAt: new Date().toISOString(),
        createdAt: new Date().toISOString(),
      };
      if (!mockFrameworks[data.projectId]) mockFrameworks[data.projectId] = [];
      mockFrameworks[data.projectId].push(profile);
      return Promise.resolve(profile);
    }
    return api.post<FrameworkProfile>('/automation/frameworks/connect', data).then(r => r.data);
  },

  generateCode: (data: {
    projectId: number;
    frameworkProfileId: number;
    suiteName: string;
    testCaseTitles?: string[];
    testCaseDescriptions?: string[];
  }): Promise<AutomationExecution> => {
    if (isDemo()) {
      const titles = data.testCaseTitles ?? ['Generated test'];
      const code = `import { test, expect } from '@playwright/test';\n\ntest.describe('${data.suiteName}', () => {\n${
        titles.map(t => `\n  test('${t}', async ({ page }) => {\n    // AI-generated test for: ${t}\n    await page.goto('https://bkumars22.github.io/${data.projectId === 1 ? 'SupplyChainPlatformProject' : 'ARIA'}');\n    await expect(page).toHaveTitle(/.+/);\n  });`).join('\n')
      }\n\n});\n`;
      const exec: AutomationExecution = {
        id: Date.now(),
        projectId: data.projectId,
        frameworkProfileId: data.frameworkProfileId,
        suiteName: data.suiteName,
        frameworkType: 'PLAYWRIGHT',
        generatedCode: code,
        status: 'QUEUED',
        totalTests: 0,
        passed: 0,
        failed: 0,
        skipped: 0,
        triggeredBy: 'admin@qaip.io',
        createdAt: new Date().toISOString(),
      };
      if (!mockExecutions[data.projectId]) mockExecutions[data.projectId] = [];
      mockExecutions[data.projectId].unshift(exec);
      return Promise.resolve(exec);
    }
    return api.post<AutomationExecution>('/automation/generate-code', data).then(r => r.data);
  },

  execute: (executionId: number, appUrl?: string): Promise<AutomationExecution> => {
    if (isDemo()) {
      const exec = getMockExecution(executionId);
      if (exec) {
        exec.status = 'PASSED';
        exec.totalTests = 3;
        exec.passed = 3;
        exec.failed = 0;
        exec.completedAt = new Date().toISOString();
      }
      return Promise.resolve(exec ?? { id: executionId } as AutomationExecution);
    }
    return api.post<AutomationExecution>(`/automation/execute/${executionId}`, null, {
      params: appUrl ? { appUrl } : {},
    }).then(r => r.data);
  },

  getExecutions: (projectId: number): Promise<AutomationExecution[]> => {
    if (isDemo()) return Promise.resolve(mockExecutions[projectId] ?? []);
    return api.get<AutomationExecution[]>(`/automation/projects/${projectId}/executions`).then(r => r.data);
  },

  getExecution: (id: number): Promise<AutomationExecution> => {
    if (isDemo()) {
      const exec = getMockExecution(id);
      return exec ? Promise.resolve(exec) : Promise.reject(new Error('Not found'));
    }
    return api.get<AutomationExecution>(`/automation/executions/${id}`).then(r => r.data);
  },

  getResults: (executionId: number): Promise<AutomationResult[]> => {
    if (isDemo()) return Promise.resolve(mockResults[executionId] ?? []);
    return api.get<AutomationResult[]>(`/automation/executions/${executionId}/results`).then(r => r.data);
  },

  getReports: (projectId: number): Promise<ReportSummary[]> => {
    if (isDemo()) return Promise.resolve([]);
    return api.get<ReportSummary[]>(`/automation/projects/${projectId}/reports`).then(r => r.data);
  },

  getFileTree: (profileId: number): Promise<FileNode[]> => {
    if (isDemo()) return Promise.resolve(mockFileTrees[profileId] ?? []);
    return api.get<FileNode[]>(`/automation/frameworks/${profileId}/file-tree`).then(r => r.data);
  },

  getFileContent: (profileId: number, path: string): Promise<FileContent> => {
    if (isDemo()) {
      const fc = mockFileContents[path];
      return fc ? Promise.resolve(fc) : Promise.reject(new Error('File not found'));
    }
    return api.get<FileContent>(`/automation/frameworks/${profileId}/file-content`, { params: { path } }).then(r => r.data);
  },

  saveFileContent: (profileId: number, data: { path: string; content: string; sha: string; commitMessage: string }): Promise<FileSaveResult> => {
    if (isDemo()) {
      if (mockFileContents[data.path]) {
        mockFileContents[data.path] = { path: data.path, content: data.content, sha: 'sha_' + Date.now() };
      }
      return Promise.resolve({ committed: true, sha: 'sha_' + Date.now(), message: data.commitMessage });
    }
    return api.put<FileSaveResult>(`/automation/frameworks/${profileId}/file-content`, data).then(r => r.data);
  },

  executeFromFramework: (profileId: number, testNames: string[], allTests: boolean): Promise<AutomationExecution> => {
    if (isDemo()) {
      const exec: AutomationExecution = {
        id: Date.now(),
        projectId: Object.values(mockFrameworks).flat().find(f => f.id === profileId)?.projectId ?? 1,
        frameworkProfileId: profileId,
        suiteName: allTests ? 'Execute All Framework Tests' : `Execute ${testNames.length} New Tests`,
        frameworkType: 'PLAYWRIGHT',
        status: 'RUNNING',
        totalTests: allTests ? 76 : testNames.length,
        passed: 0,
        failed: 0,
        skipped: 0,
        createdAt: new Date().toISOString(),
        startedAt: new Date().toISOString(),
      };
      const projectId = exec.projectId;
      if (!mockExecutions[projectId]) mockExecutions[projectId] = [];
      mockExecutions[projectId].unshift(exec);
      setTimeout(() => {
        exec.status = allTests ? 'PASSED' : 'PASSED';
        exec.passed = allTests ? 72 : testNames.length;
        exec.failed = allTests ? 4 : 0;
        exec.totalTests = allTests ? 76 : testNames.length;
        exec.completedAt = new Date().toISOString();
        exec.durationMs = allTests ? 48200 : testNames.length * 1200;
      }, 1500);
      return Promise.resolve(exec);
    }
    return api.post<AutomationExecution>(`/automation/frameworks/${profileId}/execute`, { testNames, allTests }).then(r => r.data);
  },
};
