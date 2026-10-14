import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import api from '../lib/api';

const AuthContext = createContext({
  user: null,
  loading: true,
  isAuthenticated: false,
  register: async () => {},
  login: async () => {},
  logout: () => {},
  refresh: async () => {},
  toggleFavorite: async () => {},
  openAuthModal: () => {},
  closeAuthModal: () => {},
  authModalOpen: false,
  authModalMode: 'register',
});

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [authModalMode, setAuthModalMode] = useState('register');

  const setAuth = (token, u) => {
    if (token) localStorage.setItem('eg_user_token', token);
    if (u) localStorage.setItem('eg_user', JSON.stringify(u));
    setUser(u || null);
  };

  const clearAuth = () => {
    localStorage.removeItem('eg_user_token');
    localStorage.removeItem('eg_user');
    setUser(null);
  };

  const refresh = useCallback(async () => {
    const token = localStorage.getItem('eg_user_token');
    if (!token) { setLoading(false); return; }
    try {
      const { data } = await api.get('/auth/me', { headers: { Authorization: `Bearer ${token}` } });
      setUser(data.user);
      localStorage.setItem('eg_user', JSON.stringify(data.user));
    } catch (e) {
      // Banned / expired / deleted — clear session
      const detail = e?.response?.data?.detail;
      clearAuth();
      if (e?.response?.status === 403 && detail) {
        // Defer to next tick so any Toaster is mounted
        setTimeout(() => {
          try {
            const evt = new CustomEvent('eg:notice', { detail: { title: 'Signed out', description: detail, variant: 'destructive' } });
            window.dispatchEvent(evt);
          } catch (_) { /* ignore */ }
        }, 200);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // If returning from Google OAuth, skip /auth/me — AuthCallback will
    // exchange the session_id and set our JWT first.
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    if (typeof window !== 'undefined' && window.location.hash && window.location.hash.includes('session_id=')) {
      setLoading(false);
      return;
    }
    const cached = localStorage.getItem('eg_user');
    if (cached) {
      try { setUser(JSON.parse(cached)); } catch (e) { /* ignore */ }
    }
    refresh();
  }, [refresh]);

  const register = async ({ fullName, email, password, subscribeNewsletter = true }) => {
    const { data } = await api.post('/auth/register', { fullName, email, password, subscribeNewsletter });
    setAuth(data.token, data.user);
    return data.user;
  };

  const login = async ({ email, password }) => {
    const { data } = await api.post('/auth/login', { email, password });
    setAuth(data.token, data.user);
    return data.user;
  };

  const beginGoogleSignIn = () => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    const redirectUrl = window.location.origin + '/';
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  const phoneSendCode = async (phone) => {
    const { data } = await api.post('/auth/phone/send-code', { phone });
    return data; // { ok, sentTo, existing, expiresInMinutes, resendAfterSeconds }
  };

  const phoneVerify = async ({ phone, code, fullName, email, subscribeNewsletter = true }) => {
    const { data } = await api.post('/auth/phone/verify', { phone, code, fullName, email, subscribeNewsletter });
    setAuth(data.token, data.user);
    return data.user;
  };

  const completeGoogleSignIn = async (sessionId) => {
    const { data } = await api.post('/auth/google/session', { session_id: sessionId });
    setAuth(data.token, data.user);
    return data.user;
  };

  const logout = () => { clearAuth(); };

  const toggleFavorite = async (productId) => {
    if (!localStorage.getItem('eg_user_token')) {
      setAuthModalMode('register');
      setAuthModalOpen(true);
      return { needsAuth: true };
    }
    const token = localStorage.getItem('eg_user_token');
    const { data } = await api.post(`/auth/favorites/${encodeURIComponent(productId)}`, null, {
      headers: { Authorization: `Bearer ${token}` },
    });
    setUser((u) => (u ? { ...u, favorites: data.favorites } : u));
    const cached = localStorage.getItem('eg_user');
    if (cached) {
      try {
        const parsed = JSON.parse(cached);
        parsed.favorites = data.favorites;
        localStorage.setItem('eg_user', JSON.stringify(parsed));
      } catch (e) { /* ignore */ }
    }
    return { favorited: data.favorited };
  };

  const openAuthModal = (mode = 'register') => {
    setAuthModalMode(mode);
    setAuthModalOpen(true);
  };
  const closeAuthModal = () => setAuthModalOpen(false);

  return (
    <AuthContext.Provider value={{
      user,
      loading,
      isAuthenticated: !!user,
      register,
      login,
      logout,
      refresh,
      toggleFavorite,
      openAuthModal,
      closeAuthModal,
      beginGoogleSignIn,
      completeGoogleSignIn,
      phoneSendCode,
      phoneVerify,
      authModalOpen,
      authModalMode,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
