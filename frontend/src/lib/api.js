import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

const api = axios.create({ baseURL: API });

api.interceptors.request.use((cfg) => {
  // If the caller already set an Authorization header, keep it
  if (cfg.headers && cfg.headers.Authorization) return cfg;
  // Admin routes use the admin token; everything else uses the user token when available
  const path = (cfg.url || '').toString();
  const isAdmin = path.startsWith('/admin') || path === '/upload' || path.startsWith('/upload');
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
