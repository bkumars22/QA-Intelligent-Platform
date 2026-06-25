import type { ReactNode } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import {
  LayoutDashboard,
  FolderKanban,
  LogOut,
  Brain,
  Workflow,
  ShieldCheck,
} from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import { useNavigate } from 'react-router-dom';
import { getSecurityLog } from '../services/securityMonitor';

interface NavItem {
  to: string;
  label: string;
  icon: ReactNode;
}

const navItems: NavItem[] = [
  { to: '/dashboard', label: 'Dashboard', icon: <LayoutDashboard size={18} /> },
  { to: '/projects', label: 'Projects', icon: <FolderKanban size={18} /> },
  { to: '/pipeline', label: 'QA Pipeline', icon: <Workflow size={18} /> },
];

function SecurityShield() {
  const today = new Date().toDateString();
  const todayEvents = getSecurityLog().filter(
    e => new Date(e.timestamp).toDateString() === today
  ).length;

  return (
    <div className="mx-3 mb-2 px-3 py-2 rounded-lg bg-slate-800 border border-slate-700">
      <div className="flex items-center gap-2">
        <ShieldCheck size={13} className="text-green-400 shrink-0" />
        <span className="text-xs font-semibold text-green-400">Security Shield Active</span>
        {todayEvents > 0 && (
          <span className="ml-auto text-[10px] font-bold bg-amber-500 text-white px-1.5 py-0.5 rounded-full">
            {todayEvents}
          </span>
        )}
      </div>
      <p className="text-[10px] text-slate-500 mt-0.5">
        All actions monitored · Alerts → swamy.kumar02@gmail.com
      </p>
    </div>
  );
}

export function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="w-64 flex flex-col bg-[#0f172a] text-white shrink-0">
        {/* Logo */}
        <div className="flex items-center gap-3 px-6 py-5 border-b border-slate-700">
          <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-brand-600">
            <Brain size={20} className="text-white" />
          </div>
          <div>
            <p className="font-bold text-base leading-tight">QA Intelligent</p>
            <p className="text-xs text-slate-400 leading-tight">AI-Driven Platform</p>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-brand-600 text-white'
                    : 'text-slate-300 hover:bg-slate-700 hover:text-white'
                }`
              }
            >
              {item.icon}
              {item.label}
            </NavLink>
          ))}
        </nav>

        {/* Security shield badge */}
        <SecurityShield />

        {/* User info + logout */}
        <div className="px-4 py-4 border-t border-slate-700">
          {user && (
            <div className="mb-3">
              <p className="text-sm font-medium text-white truncate">{user.email}</p>
              <p className="text-xs text-slate-400 mt-0.5">{user.role.replace('_', ' ')}</p>
            </div>
          )}
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 w-full px-3 py-2 text-sm text-slate-300 hover:text-white hover:bg-slate-700 rounded-lg transition-colors"
          >
            <LogOut size={16} />
            Sign out
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  );
}
