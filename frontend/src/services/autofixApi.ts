import axios from 'axios';
import { getToken } from './api';
import { DEMO_TOKEN, mockAutofixAudit } from './mockData';
import type { AutofixAuditEntry } from './mockData';

export type { AutofixAuditEntry } from './mockData';

const base = '/api';

function authHeaders() {
  return { Authorization: `Bearer ${getToken()}` };
}

function isDemo(): boolean {
  return getToken() === DEMO_TOKEN;
}

export const autofixApi = {
  list: (filters?: { projectId?: number; status?: string }): Promise<AutofixAuditEntry[]> => {
    if (isDemo()) {
      let rows = mockAutofixAudit;
      if (filters?.projectId) rows = rows.filter(r => r.projectId === filters.projectId);
      if (filters?.status) rows = rows.filter(r => r.status === filters.status);
      return Promise.resolve(rows);
    }
    const params = new URLSearchParams();
    if (filters?.projectId) params.set('projectId', String(filters.projectId));
    if (filters?.status) params.set('status', filters.status);
    const qs = params.toString();
    return axios
      .get<AutofixAuditEntry[]>(`${base}/autofix-audit${qs ? `?${qs}` : ''}`, { headers: authHeaders() })
      .then(r => r.data);
  },
};
