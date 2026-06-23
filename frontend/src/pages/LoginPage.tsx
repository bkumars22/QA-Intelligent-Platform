import { useState, useEffect, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { Brain, AlertCircle, Wifi, WifiOff, Loader } from 'lucide-react';
import axios from 'axios';
import { useAuth } from '../hooks/useAuth';

type BackendStatus = 'checking' | 'online' | 'offline';

const BACKEND_URL = import.meta.env.VITE_API_URL ?? '';

async function pingBackend(): Promise<boolean> {
  try {
    const url = BACKEND_URL ? `${BACKEND_URL}/api/health` : '/api/health';
    const res = await fetch(url, { signal: AbortSignal.timeout(6000) });
    return res.ok;
  } catch {
    return false;
  }
}

function isNetworkFailure(err: unknown): boolean {
  // Axios: no response object means the server was unreachable
  if (axios.isAxiosError(err) && !err.response) return true;
  if (err instanceof TypeError) return true;
  if (err instanceof Error) {
    const msg = err.message.toLowerCase();
    return msg.includes('network') || msg.includes('failed to fetch') || msg.includes('err_network');
  }
  return false;
}

export function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [backendStatus, setBackendStatus] = useState<BackendStatus>('checking');
  const { login, demoLogin } = useAuth();
  const navigate = useNavigate();

  // Ping the backend on mount so the user sees live status before trying to log in
  useEffect(() => {
    pingBackend().then((ok) => setBackendStatus(ok ? 'online' : 'offline'));
  }, []);

  const handleDemo = () => {
    demoLogin();
    navigate('/dashboard');
  };

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    // Only the plain shorthand 'admin' / 'admin' triggers instant demo
    // Every real email address always goes to the backend
    const trimmedEmail = email.trim();
    if (trimmedEmail === 'admin' && password === 'admin') {
      demoLogin();
      navigate('/dashboard');
      return;
    }

    try {
      await login(trimmedEmail, password);
      navigate('/dashboard');
    } catch (err: unknown) {
      if (isNetworkFailure(err)) {
        setError(
          'Cannot reach the backend. Use "Enter as Demo Admin" to explore the platform, ' +
          'or contact the administrator to check Railway deployment.'
        );
      } else {
        setError('Invalid email or password. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-screen">
      {/* Left sidebar / branding panel */}
      <div className="hidden lg:flex lg:w-1/2 bg-[#0f172a] flex-col justify-between p-12">
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-brand-600">
            <Brain size={22} className="text-white" />
          </div>
          <span className="text-white font-bold text-xl">QA Intelligent Platform</span>
        </div>

        <div>
          <h1 className="text-4xl font-bold text-white leading-tight">
            QA Intelligent Platform (AI-Driven)
          </h1>
          <p className="mt-4 text-slate-400 text-lg leading-relaxed">
            Automated test generation, defect detection, and risk analysis
            powered by multi-agent AI. Ship with confidence.
          </p>
          <div className="mt-10 space-y-4">
            {[
              { label: 'Risk Analysis', desc: 'ML-powered file-level risk scoring from git history' },
              { label: 'Auto Test Gen', desc: 'Coverage gap detection + Playwright test synthesis' },
              { label: 'Defect AI', desc: 'Explain root causes and suggest fixes instantly' },
            ].map((f) => (
              <div key={f.label} className="flex items-start gap-3">
                <span className="mt-0.5 h-5 w-5 rounded-full bg-brand-600 flex items-center justify-center shrink-0">
                  <span className="block h-2 w-2 rounded-full bg-white" />
                </span>
                <div>
                  <p className="text-white font-medium text-sm">{f.label}</p>
                  <p className="text-slate-400 text-sm">{f.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <p className="text-slate-500 text-sm">© 2026 QA Intelligent Platform. All rights reserved.</p>
      </div>

      {/* Right — login form */}
      <div className="flex-1 flex items-center justify-center bg-gray-50 px-6 py-12">
        <div className="w-full max-w-md">
          {/* Mobile logo */}
          <div className="flex lg:hidden items-center gap-2 mb-8">
            <div className="flex items-center justify-center w-9 h-9 rounded-xl bg-brand-600">
              <Brain size={20} className="text-white" />
            </div>
            <span className="font-bold text-xl text-gray-900">QA Intelligent Platform</span>
          </div>

          <h2 className="text-2xl font-bold text-gray-900">Sign in to your account</h2>

          {/* Live backend status */}
          <div className="mt-2 flex items-center gap-2">
            {backendStatus === 'checking' && (
              <><Loader size={13} className="text-gray-400 animate-spin" /><span className="text-xs text-gray-400">Checking backend…</span></>
            )}
            {backendStatus === 'online' && (
              <><Wifi size={13} className="text-green-500" /><span className="text-xs text-green-600 font-medium">Backend online — sign in with your account</span></>
            )}
            {backendStatus === 'offline' && (
              <><WifiOff size={13} className="text-amber-500" /><span className="text-xs text-amber-600 font-medium">Backend offline — use Demo Admin or try admin / admin</span></>
            )}
          </div>

          {/* Demo access — no backend required */}
          <div className="mt-5 p-4 rounded-xl bg-blue-50 border border-blue-200">
            <p className="text-sm font-medium text-blue-800 mb-1">Try the demo instantly</p>
            <p className="text-xs text-blue-600 mb-3">Access the full dashboard without any credentials. No account needed.</p>
            <button
              type="button"
              onClick={handleDemo}
              className="w-full py-2.5 px-4 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition-colors text-sm"
            >
              Enter as Demo Admin
            </button>
          </div>

          <div className="mt-5 flex items-center gap-3">
            <div className="flex-1 h-px bg-gray-200" />
            <span className="text-xs text-gray-400">or sign in with your account</span>
            <div className="flex-1 h-px bg-gray-200" />
          </div>

          <form onSubmit={handleSubmit} className="mt-5 space-y-5">
            {error && (
              <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 border border-red-200 text-red-700">
                <AlertCircle size={16} className="shrink-0" />
                <span className="text-sm">{error}</span>
              </div>
            )}

            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
                Email address
              </label>
              <input
                id="email"
                type="text"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-2.5 rounded-lg border border-gray-300 focus:ring-2 focus:ring-brand-500 focus:border-brand-500 outline-none text-sm text-gray-900 bg-white transition"
                placeholder="admin"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
                Password
              </label>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-2.5 rounded-lg border border-gray-300 focus:ring-2 focus:ring-brand-500 focus:border-brand-500 outline-none text-sm text-gray-900 bg-white transition"
                placeholder="••••••••"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 px-4 bg-brand-600 hover:bg-brand-700 disabled:bg-brand-500 disabled:opacity-60 text-white font-semibold rounded-lg transition-colors text-sm flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <span className="h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Signing in…
                </>
              ) : (
                'Sign in'
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
