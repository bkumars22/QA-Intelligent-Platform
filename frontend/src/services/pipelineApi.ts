import axios from 'axios';
import { getToken } from './api';
import {
  DEMO_TOKEN,
  mockPipelineRuns,
  mockStoryAnalysis,
  mockGapReports,
  mockTestCases,
  mockExecutionResults,
  mockGeneratedCode,
  getMockPipelineRun,
} from './mockData';

const base = '/api';

function authHeaders() {
  return { Authorization: `Bearer ${getToken()}` };
}

function isDemo(): boolean {
  return getToken() === DEMO_TOKEN;
}

export interface PipelineStartPayload {
  projectId: number;
  jiraStoryId: string;
}

export interface PipelineRun {
  id: number;
  projectId: number;
  jiraStoryId: string;
  jiraSummary: string;
  status: string;
  currentStage: number;
  startedAt: string;
  completedAt?: string;
  reportUrl?: string;
  errorMessage?: string;
}

export interface StoryAnalysis {
  id: number;
  jiraStoryId: string;
  jiraSummary: string;
  businessRules: string;
  acceptanceCriteria: string;
  edgeCases: string;
  dataRules: string;
  analyzedAt: string;
}

export interface GapReport {
  id: number;
  gapCategory: string;
  description: string;
  priorityScore: number;
  affectedRequirement: string;
}

export interface TestCase {
  id: number;
  pipelineRunId: number;
  title: string;
  testType: string;
  gapCategory: string;
  preconditions: string;
  testSteps: string;
  expectedResult: string;
  priority: string;
  status: string;
  reviewerNotes?: string;
  reviewedAt?: string;
}

export interface ExecutionResult {
  id: number;
  testCaseId: number;
  testCaseTitle: string;
  status: string;
  durationMs?: number;
  screenshotUrl?: string;
  errorMessage?: string;
  aiExplanation?: string;
  deepevalScore?: number;
}

export interface GeneratedFile {
  id: number;
  framework: string;
  filename: string;
  content: string;
  language: string;
}

export const pipelineApi = {
  start: (payload: PipelineStartPayload): Promise<PipelineRun> => {
    if (isDemo()) {
      const runs = mockPipelineRuns[payload.projectId] ?? [];
      const existing = runs[0];
      if (existing) return Promise.resolve(existing);
      const newRun: PipelineRun = {
        id: Date.now(),
        projectId: payload.projectId,
        jiraStoryId: payload.jiraStoryId,
        jiraSummary: `${payload.jiraStoryId} — AI analysis in progress`,
        status: 'STAGE_1',
        currentStage: 1,
        startedAt: new Date().toISOString(),
      };
      if (!mockPipelineRuns[payload.projectId]) mockPipelineRuns[payload.projectId] = [];
      mockPipelineRuns[payload.projectId].unshift(newRun);
      return Promise.resolve(newRun);
    }
    return axios.post<PipelineRun>(`${base}/pipeline/start`, payload, { headers: authHeaders() }).then(r => r.data);
  },

  list: (projectId: number): Promise<PipelineRun[]> => {
    if (isDemo()) {
      // Return all runs across both projects when projectId is 0 or 1
      if (projectId <= 1) {
        const all = Object.values(mockPipelineRuns).flat();
        return Promise.resolve(all);
      }
      return Promise.resolve(mockPipelineRuns[projectId] ?? []);
    }
    return axios.get<PipelineRun[]>(`${base}/pipeline?projectId=${projectId}`, { headers: authHeaders() }).then(r => r.data);
  },

  get: (id: number): Promise<PipelineRun> => {
    if (isDemo()) {
      const run = getMockPipelineRun(id);
      return run ? Promise.resolve(run) : Promise.reject(new Error('Pipeline run not found'));
    }
    return axios.get<PipelineRun>(`${base}/pipeline/${id}`, { headers: authHeaders() }).then(r => r.data);
  },

  resume: (id: number): Promise<PipelineRun> => {
    if (isDemo()) {
      const run = getMockPipelineRun(id);
      if (run) { run.status = 'STAGE_4'; run.currentStage = 4; }
      return Promise.resolve(run ?? {} as PipelineRun);
    }
    return axios.post<PipelineRun>(`${base}/pipeline/${id}/resume`, {}, { headers: authHeaders() }).then(r => r.data);
  },

  getStory: (id: number): Promise<StoryAnalysis> => {
    if (isDemo()) {
      const story = mockStoryAnalysis[id];
      return story ? Promise.resolve(story) : Promise.reject(new Error('Story not found'));
    }
    return axios.get<StoryAnalysis>(`${base}/pipeline/${id}/story`, { headers: authHeaders() }).then(r => r.data);
  },

  getGaps: (id: number): Promise<GapReport[]> => {
    if (isDemo()) return Promise.resolve(mockGapReports[id] ?? []);
    return axios.get<GapReport[]>(`${base}/pipeline/${id}/gaps`, { headers: authHeaders() }).then(r => r.data);
  },

  getTestCases: (pipelineRunId: number): Promise<TestCase[]> => {
    if (isDemo()) return Promise.resolve(mockTestCases[pipelineRunId] ?? []);
    return axios.get<TestCase[]>(`${base}/test-cases?pipelineRunId=${pipelineRunId}`, { headers: authHeaders() }).then(r => r.data);
  },

  reviewTestCase: (id: number, payload: { status: string; reviewerNotes?: string; updatedTitle?: string; updatedExpectedResult?: string }): Promise<TestCase> => {
    if (isDemo()) {
      const all = Object.values(mockTestCases).flat();
      const tc = all.find(t => t.id === id);
      if (tc) { tc.status = payload.status; tc.reviewerNotes = payload.reviewerNotes; }
      return Promise.resolve(tc ?? {} as TestCase);
    }
    return axios.patch<TestCase>(`${base}/test-cases/${id}/review`, payload, { headers: authHeaders() }).then(r => r.data);
  },

  approveAll: (pipelineRunId: number): Promise<void> => {
    if (isDemo()) {
      const cases = mockTestCases[pipelineRunId] ?? [];
      cases.forEach(tc => { tc.status = 'APPROVED'; });
      const run = getMockPipelineRun(pipelineRunId);
      if (run) { run.status = 'STAGE_4'; run.currentStage = 4; }
      return Promise.resolve();
    }
    return axios.post(`${base}/test-cases/approve-all?pipelineRunId=${pipelineRunId}`, {}, { headers: authHeaders() }).then(r => r.data);
  },

  getExecutions: (id: number): Promise<ExecutionResult[]> => {
    if (isDemo()) return Promise.resolve(mockExecutionResults[id] ?? []);
    return axios.get<ExecutionResult[]>(`${base}/pipeline/${id}/executions`, { headers: authHeaders() }).then(r => r.data);
  },

  getGeneratedCode: (id: number): Promise<GeneratedFile[]> => {
    if (isDemo()) return Promise.resolve(mockGeneratedCode[id] ?? []);
    return axios.get<GeneratedFile[]>(`${base}/pipeline/${id}/code`, { headers: authHeaders() }).then(r => r.data);
  },
};
