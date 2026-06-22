import { useState, useCallback, useEffect } from 'react';
import { login as apiLogin, setToken, clearToken } from '../services/api';
import type { User, UserRole } from '../types';

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
}

interface UseAuthReturn {
  user: User | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const STORAGE_KEY = 'qaip_auth';

function loadFromStorage(): AuthState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { user: null, isAuthenticated: false };
    const parsed = JSON.parse(raw) as { token: string; user: User };
    setToken(parsed.token);
    return { user: parsed.user, isAuthenticated: true };
  } catch {
    return { user: null, isAuthenticated: false };
  }
}

function saveToStorage(token: string, user: User): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify({ token, user }));
}

function clearStorage(): void {
  localStorage.removeItem(STORAGE_KEY);
}

// Restore session on module load — survives page refresh and direct URL navigation
let _authState: AuthState = loadFromStorage();
const _listeners = new Set<() => void>();

function notifyListeners(): void {
  _listeners.forEach((fn) => fn());
}

export function useAuth(): UseAuthReturn {
  const [, rerender] = useState(0);

  useEffect(() => {
    const fn = () => rerender((n) => n + 1);
    _listeners.add(fn);
    return () => {
      _listeners.delete(fn);
    };
  }, []);

  const login = useCallback(async (email: string, password: string): Promise<void> => {
    const response = await apiLogin(email, password);
    setToken(response.accessToken);
    const user: User = {
      id: 0,
      email: response.email,
      role: response.role as UserRole,
    };
    saveToStorage(response.accessToken, user);
    _authState = { user, isAuthenticated: true };
    notifyListeners();
  }, []);

  const logout = useCallback((): void => {
    clearToken();
    clearStorage();
    _authState = { user: null, isAuthenticated: false };
    notifyListeners();
  }, []);

  return {
    user: _authState.user,
    isAuthenticated: _authState.isAuthenticated,
    login,
    logout,
  };
}
