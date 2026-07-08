import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

const api = axios.create({ baseURL: API });

api.interceptors.request.use((cfg) => {
  // If the caller already set an Authorization header, keep it
  if (cfg.headers && cfg.headers.Authorization) return cfg;
  const path = (cfg.url || '').toString();
  // Any request initiated from an admin page, or targeting an admin-only backend route,
  // must use the admin token — even if the user is also signed in as a member.
  const onAdminPage = typeof window !== 'undefined' && window.location?.pathname?.startsWith('/admin');
  const adminOnlyRoute = path.startsWith('/admin') || path.startsWith('/upload') || path.startsWith('/site') || path.startsWith('/subscribers') || path.startsWith('/users') || path.startsWith('/ai-edit');
  const isAdmin = onAdminPage || adminOnlyRoute;
  const token = isAdmin
    ? localStorage.getItem('eg_admin_token')
    : (localStorage.getItem('eg_user_token') || localStorage.getItem('eg_admin_token'));
  if (token) cfg.headers.Authorization = `Bearer ${token}`;
  return cfg;
});

export function resolveMediaUrl(url) {
  if (!url) return '';
  if (url.startsWith('http://') || url.startsWith('https://')) return url;
  if (url.startsWith('/api/')) return `${BACKEND_URL}${url}`;
  return url;
}

export default api;
