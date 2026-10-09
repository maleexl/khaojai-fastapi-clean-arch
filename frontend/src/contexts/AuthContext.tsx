import { createContext, useContext, useState, useEffect } from 'react';
import type { ReactNode } from 'react';
import { apiCall } from '../api/client';
import type { User, TokenResponse } from '../api/client';

interface AuthContextType {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(() => localStorage.getItem('access_token'));
  const [refreshToken, setRefreshToken] = useState<string | null>(() => localStorage.getItem('refresh_token'));

  async function login(email: string, password: string) {
    const tokens = await apiCall<TokenResponse>('/api/v1/users/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    localStorage.setItem('access_token', tokens.access_token);
    localStorage.setItem('refresh_token', tokens.refresh_token);
    setAccessToken(tokens.access_token);
    setRefreshToken(tokens.refresh_token);
  }

  async function logout() {
    try {
      if (refreshToken) {
        await apiCall('/api/v1/users/logout', { method: 'POST' }, refreshToken);
      }
    } catch {
      /* ignore */
    }
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setAccessToken(null);
    setRefreshToken(null);
    setUser(null);
  }

  async function refreshUser() {
    if (!accessToken) return;
    try {
      const me = await apiCall<User>('/api/v1/users/me');
      setUser(me);
    } catch {
      setUser(null);
    }
  }

  useEffect(() => {
    if (accessToken) refreshUser();
    else setUser(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accessToken]);

  return (
    <AuthContext.Provider
      value={{ user, accessToken, refreshToken, isAuthenticated: !!accessToken, login, logout, refreshUser }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
