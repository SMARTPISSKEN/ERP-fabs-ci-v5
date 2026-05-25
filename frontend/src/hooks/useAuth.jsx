import { useEffect, useState, useCallback, useContext, createContext } from "react";
import axios from "axios";

const API = "/api";  // Relative path - will be proxied to backend via package.json proxy
const TOKEN_KEY = "fabsci_access_token";

export const tokenStore = {
  get: () => (typeof window === "undefined" ? null : localStorage.getItem(TOKEN_KEY)),
  set: (t) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

// Inject Authorization header on every API call when token is present.
axios.interceptors.request.use((config) => {
  const t = tokenStore.get();
  if (t && config.url && config.url.startsWith('/api')) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${t}`;
  }
  return config;
});

const AuthCtx = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isLoading, setLoading] = useState(true);

  const checkAuth = useCallback(async () => {
    if (!tokenStore.get()) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const r = await axios.get(`${API}/auth/me`);
      setUser(r.data);
    } catch {
      tokenStore.clear();
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  const login = useCallback(async (email, password) => {
    const r = await axios.post(`${API}/auth/login`, { email, password });
    if (r.data?.access_token) {
      tokenStore.set(r.data.access_token);
    }
    setUser(r.data.user);
    return r.data.user;
  }, []);

  const logout = useCallback(async () => {
    try {
      await axios.post(`${API}/auth/logout`, {});
    } catch (_) {
      /* ignore */
    }
    tokenStore.clear();
    setUser(null);
    window.location.href = "/login";
  }, []);

  return (
    <AuthCtx.Provider value={{ user, isLoading, role: user?.role, setUser, refresh: checkAuth, login, logout }}>
      {children}
    </AuthCtx.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthCtx);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
