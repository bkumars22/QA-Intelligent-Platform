/**
 * QAIP Security Shield
 *
 * Detects, logs, and emails alerts to swamy.kumar02@gmail.com for:
 *  - DELETE_ATTEMPT      — blocked delete button clicked
 *  - CREATE_ATTEMPT      — blocked new project button clicked
 *  - LOGIN_BRUTE_FORCE   — 3+ failed logins within 5 minutes
 *  - XSS_ATTEMPT         — script/injection pattern in any input
 *  - SQL_INJECTION        — SQL keyword pattern in any input
 *  - RAPID_FIRE           — 15+ actions in 10 seconds (bot/stress)
 *  - SUSPICIOUS_INPUT     — unexpected characters in structured fields
 */

import emailjs from '@emailjs/browser';

// ─── Types ────────────────────────────────────────────────────────────────────

export type SecurityEventType =
  | 'DELETE_ATTEMPT'
  | 'CREATE_ATTEMPT'
  | 'LOGIN_BRUTE_FORCE'
  | 'XSS_ATTEMPT'
  | 'SQL_INJECTION'
  | 'RAPID_FIRE'
  | 'SUSPICIOUS_INPUT';

interface SecurityEvent {
  type: SecurityEventType;
  detail: string;
  projectId?: number;
  timestamp: string;
  userAgent: string;
  pageUrl: string;
}

// ─── Config ───────────────────────────────────────────────────────────────────

const ALERT_EMAIL = 'swamy.kumar02@gmail.com';
const LOG_KEY = 'qaip_security_log';
const LOGIN_FAIL_KEY = 'qaip_login_fails';
const COOLDOWN_MS = 60_000;         // max 1 email per minute
const LOGIN_WINDOW_MS = 5 * 60_000; // brute-force window: 5 minutes
const RAPID_FIRE_WINDOW_MS = 10_000;
const RAPID_FIRE_THRESHOLD = 15;

let lastEmailAt = 0;
const recentActions: number[] = [];

// ─── Audit log (localStorage) ─────────────────────────────────────────────────

function readLog(): SecurityEvent[] {
  try { return JSON.parse(localStorage.getItem(LOG_KEY) ?? '[]'); } catch { return []; }
}

function writeLog(events: SecurityEvent[]): void {
  const trimmed = events.slice(-200);
  try { localStorage.setItem(LOG_KEY, JSON.stringify(trimmed)); } catch { /* storage full */ }
}

function todayCount(): number {
  const today = new Date().toDateString();
  return readLog().filter(e => new Date(e.timestamp).toDateString() === today).length;
}

// ─── Email alert ──────────────────────────────────────────────────────────────

function sendEmail(event: SecurityEvent): void {
  const serviceId  = import.meta.env.VITE_EMAILJS_SERVICE_ID  ?? '';
  const templateId = import.meta.env.VITE_EMAILJS_TEMPLATE_ID ?? '';
  const publicKey  = import.meta.env.VITE_EMAILJS_PUBLIC_KEY  ?? '';
  if (!serviceId || !templateId || !publicKey) return;

  const now = Date.now();
  if (now - lastEmailAt < COOLDOWN_MS) return;
  lastEmailAt = now;

  emailjs.send(serviceId, templateId, {
    to_email:    ALERT_EMAIL,
    event_type:  event.type,
    event_detail: event.detail,
    project_id:  event.projectId != null ? String(event.projectId) : 'N/A',
    timestamp:   new Date(event.timestamp).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' }),
    user_agent:  event.userAgent,
    page_url:    event.pageUrl,
    total_today: String(todayCount()),
  }, publicKey).catch(() => { /* silent — never break the app */ });
}

// ─── Core log function ────────────────────────────────────────────────────────

export function logSecurityEvent(
  type: SecurityEventType,
  detail: string,
  projectId?: number
): void {
  const event: SecurityEvent = {
    type,
    detail,
    projectId,
    timestamp: new Date().toISOString(),
    userAgent: navigator.userAgent.slice(0, 250),
    pageUrl:   window.location.href,
  };

  console.warn('[QAIP Security Shield]', event);

  const log = readLog();
  log.push(event);
  writeLog(log);

  sendEmail(event);
}

// ─── Login brute-force tracking ───────────────────────────────────────────────

export function recordLoginFailure(): { shouldLockout: boolean; failCount: number } {
  const now = Date.now();
  let fails: number[] = [];
  try { fails = JSON.parse(localStorage.getItem(LOGIN_FAIL_KEY) ?? '[]'); } catch { fails = []; }

  fails = fails.filter(t => now - t < LOGIN_WINDOW_MS);
  fails.push(now);
  try { localStorage.setItem(LOGIN_FAIL_KEY, JSON.stringify(fails)); } catch { /* ignore */ }

  if (fails.length === 3) {
    logSecurityEvent('LOGIN_BRUTE_FORCE', `3 consecutive failed login attempts within 5 minutes`);
  } else if (fails.length > 3) {
    logSecurityEvent('LOGIN_BRUTE_FORCE', `${fails.length} failed login attempts — persistent attacker`);
  }

  return { shouldLockout: fails.length >= 5, failCount: fails.length };
}

export function clearLoginFailures(): void {
  localStorage.removeItem(LOGIN_FAIL_KEY);
}

export function getLoginFailCount(): number {
  try {
    const now = Date.now();
    const fails: number[] = JSON.parse(localStorage.getItem(LOGIN_FAIL_KEY) ?? '[]');
    return fails.filter(t => now - t < LOGIN_WINDOW_MS).length;
  } catch { return 0; }
}

// ─── Rapid-fire detection ─────────────────────────────────────────────────────

export function recordAction(): void {
  const now = Date.now();
  recentActions.push(now);
  const recent = recentActions.filter(t => now - t < RAPID_FIRE_WINDOW_MS);
  recentActions.length = 0;
  recentActions.push(...recent);
  if (recent.length >= RAPID_FIRE_THRESHOLD) {
    logSecurityEvent('RAPID_FIRE', `${recent.length} actions within ${RAPID_FIRE_WINDOW_MS / 1000}s — possible automated attack`);
  }
}

// ─── Input sanitization ───────────────────────────────────────────────────────

const XSS_PATTERNS: RegExp[] = [
  /<script[\s\S]*?>/i,
  /javascript\s*:/i,
  /on\w+\s*=/i,
  /<iframe/i,
  /document\.cookie/i,
  /document\.write/i,
  /eval\s*\(/i,
  /window\.location/i,
  /<img[^>]+src[^>]*>/i,
  /data:\s*text\/html/i,
];

const SQL_PATTERNS: RegExp[] = [
  /(\bSELECT\b|\bINSERT\b|\bUPDATE\b|\bDELETE\b|\bDROP\b|\bUNION\b|\bCREATE\b|\bALTER\b|\bEXEC\b)/i,
  /--\s/,
  /\/\*[\s\S]*?\*\//,
  /\bOR\b\s+['"]?\d+['"]?\s*=\s*['"]?\d+/i,
  /\bAND\b\s+['"]?\d+['"]?\s*=\s*['"]?\d+/i,
  /xp_cmdshell/i,
];

export function sanitizeInput(value: string, fieldName: string): string {
  for (const pattern of XSS_PATTERNS) {
    if (pattern.test(value)) {
      logSecurityEvent('XSS_ATTEMPT', `XSS pattern detected in field "${fieldName}": ${value.slice(0, 100)}`);
      return value.replace(/<[^>]*>/g, '').replace(/[<>"'`]/g, '').trim();
    }
  }
  for (const pattern of SQL_PATTERNS) {
    if (pattern.test(value)) {
      logSecurityEvent('SQL_INJECTION', `SQL injection attempt in field "${fieldName}": ${value.slice(0, 100)}`);
      return value.replace(/[;'"\\]/g, '').trim();
    }
  }
  return value;
}

// ─── Security log export (for debug) ─────────────────────────────────────────

export function getSecurityLog(): SecurityEvent[] {
  return readLog();
}

export function clearSecurityLog(): void {
  localStorage.removeItem(LOG_KEY);
}
