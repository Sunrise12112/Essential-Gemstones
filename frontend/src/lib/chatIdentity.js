// Utilities for identifying the current chat principal (auth token or anonymous client id)

const CLIENT_ID_KEY = 'eg_client_id';

export function getClientId() {
  let id = localStorage.getItem(CLIENT_ID_KEY);
  if (!id) {
    // eslint-disable-next-line no-undef
    id = (crypto?.randomUUID?.() || String(Date.now()) + Math.random().toString(36).slice(2));
    localStorage.setItem(CLIENT_ID_KEY, id);
  }
  return id;
}

export function chatAuthHeaders({ adminToken } = {}) {
  const headers = { 'X-Client-Id': getClientId() };
  const token = adminToken || localStorage.getItem('eg_user_token') || localStorage.getItem('eg_admin_token');
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}
