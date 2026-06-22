import { Navigate, Route, Routes } from 'react-router-dom';
import { useAuth } from './hooks/useAuth';
import { Layout } from './components/Layout';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { UnifiedDashboardPage } from './pages/UnifiedDashboardPage';
import { ProjectsPage } from './pages/ProjectsPage';
import { ProjectDetailPage } from './pages/ProjectDetailPage';
import { DefectDetailPage } from './pages/DefectDetailPage';
import { TestRunPage } from './pages/TestRunPage';
import { PipelinePage } from './pages/PipelinePage';
import { PipelineDetailPage } from './pages/PipelineDetailPage';
import { PipelineExecutionPage } from './pages/PipelineExecutionPage';
import { PipelineCodePage } from './pages/PipelineCodePage';
import type { ReactNode } from 'react';

interface ProtectedRouteProps {
  children: ReactNode;
}

function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      {/* Public */}
      <Route path="/login" element={<LoginPage />} />

      {/* Protected — wrapped in Layout */}
      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route path="/dashboard" element={<UnifiedDashboardPage />} />
        <Route path="/dashboard/legacy" element={<DashboardPage />} />
        <Route path="/projects" element={<ProjectsPage />} />
        <Route path="/projects/:id" element={<ProjectDetailPage />} />
        <Route path="/defects/:id" element={<DefectDetailPage />} />
        <Route path="/test-runs/:id" element={<TestRunPage />} />
        <Route path="/pipeline" element={<PipelinePage />} />
        <Route path="/pipeline/:id" element={<PipelineDetailPage />} />
        <Route path="/pipeline/:id/executions" element={<PipelineExecutionPage />} />
        <Route path="/pipeline/:id/code" element={<PipelineCodePage />} />
      </Route>

      {/* Default redirect */}
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
