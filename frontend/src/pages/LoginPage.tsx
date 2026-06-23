import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { Brain, AlertCircle } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';

export function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const { login, demoLogin } = useAuth();
  const navigate = useNavigate();

  const handleDemo = () => {
    demoLogin();
    navigate('/dashboard');
  };

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email, password);
      navigate('/dashboard');
    } catch (err: unknown) {
      const isNetworkError =
        err instanceof TypeError ||
        (err instanceof Error && (err.message.includes('fetch') || err.message.includes('network') || err.message.includes('Failed')));
      if (isNetworkError) {
        setError('Backend is not reachable. Use "Enter as Demo Admin" above to access the dashboard, or deploy the backend and try again.');
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
          <p className="mt-1 text-sm text-gray-500">Enter your credentials to access the dashboard</p>

          {/* Demo access — no backend required */}
          <div className="mt-6 p-4 rounded-xl bg-blue-50 border border-blue-200">
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
                placeholder="admin@qaip.io or admin"
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
