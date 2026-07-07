import React, { useEffect, useState } from 'react';
import { RefreshCw, Trash2, Download, UserX, UserCheck, Search } from 'lucide-react';
import api from '../../lib/api';
import { useToast } from '../../hooks/use-toast';

export default function UsersManager() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');
  const { toast } = useToast();

  const load = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('eg_admin_token');
      const { data } = await api.get('/admin/users', { headers: { Authorization: `Bearer ${token}` } });
      setUsers(data);
    } catch (e) {
      toast({ title: 'Failed to load users', description: e?.response?.data?.detail || e.message, variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, []);

  const setBanned = async (u, isBanned) => {
    try {
      const token = localStorage.getItem('eg_admin_token');
      await api.put(`/admin/users/${u.id}`, { isBanned }, { headers: { Authorization: `Bearer ${token}` } });
      toast({ title: isBanned ? 'Account suspended' : 'Account restored', description: u.email });
      load();
    } catch (e) {
      toast({ title: 'Update failed', description: e?.response?.data?.detail || e.message, variant: 'destructive' });
    }
  };

  const remove = async (u) => {
    if (!window.confirm(`Delete account for ${u.email}? This cannot be undone.`)) return;
    try {
      const token = localStorage.getItem('eg_admin_token');
      await api.delete(`/admin/users/${u.id}`, { headers: { Authorization: `Bearer ${token}` } });
      toast({ title: 'Deleted', description: u.email });
      load();
    } catch (e) {
      toast({ title: 'Delete failed', description: e?.response?.data?.detail || e.message, variant: 'destructive' });
    }
  };

  const exportCsv = () => {
    if (users.length === 0) return;
    const rows = [['fullName', 'email', 'isBanned', 'favorites', 'createdAt'], ...users.map((u) => [u.fullName, u.email, u.isBanned, (u.favorites || []).join('|'), u.createdAt])];
    const csv = rows.map((r) => r.map((v) => `"${String(v ?? '').replace(/"/g, '""')}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `members-${new Date().toISOString().slice(0,10)}.csv`;
    document.body.appendChild(a); a.click(); a.remove();
    URL.revokeObjectURL(url);
  };

  const filtered = users.filter((u) => {
    if (!query) return true;
    const q = query.toLowerCase();
    return (u.fullName || '').toLowerCase().includes(q) || (u.email || '').toLowerCase().includes(q);
  });

  return (
    <div className="space-y-5">
      <p className="text-sm text-[#5a4a3d]">People who created an Essential Gemstones account. Suspend to block their login, or delete to remove the account entirely.</p>

      <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between">
        <div className="relative flex-1 max-w-sm">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[#8b6b4f]" />
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search name or email" className="w-full pl-9 pr-4 py-2.5 border border-[#e8dfd1] rounded-lg focus:border-[#6b4f3a] focus:outline-none text-sm bg-white" />
        </div>
        <div className="flex items-center gap-2">
          <button onClick={load} className="inline-flex items-center gap-2 px-3 py-2 text-xs border border-[#e8dfd1] rounded-lg hover:bg-[#faf6f0]"><RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} /> Refresh</button>
          <button onClick={exportCsv} disabled={users.length === 0} className="inline-flex items-center gap-2 px-3 py-2 text-xs border border-[#e8dfd1] rounded-lg hover:bg-[#faf6f0] disabled:opacity-50"><Download className="w-3 h-3" /> Export CSV</button>
        </div>
      </div>

      <div>
        <h4 className="font-serif text-lg text-[#1a1410] mb-3">{users.length} member{users.length === 1 ? '' : 's'} <span className="text-xs text-[#8b6b4f] font-sans">({users.filter((u) => u.isBanned).length} suspended)</span></h4>

        {loading ? (
          <div className="flex items-center gap-2 text-sm text-[#6b4f3a]"><RefreshCw className="w-4 h-4 animate-spin" /> Loading…</div>
        ) : users.length === 0 ? (
          <p className="text-sm text-[#8b6b4f] italic py-8 text-center border border-dashed border-[#e8dfd1] rounded-2xl">No members yet.</p>
        ) : filtered.length === 0 ? (
          <p className="text-sm text-[#8b6b4f] italic py-8 text-center border border-dashed border-[#e8dfd1] rounded-2xl">No matches for &ldquo;{query}&rdquo;.</p>
        ) : (
          <div className="border border-[#e8dfd1] rounded-2xl overflow-hidden divide-y divide-[#e8dfd1]">
            {filtered.map((u) => (
              <div key={u.id} className={`flex flex-col sm:flex-row sm:items-center justify-between gap-3 px-5 py-4 ${u.isBanned ? 'bg-red-50/50' : 'bg-white hover:bg-[#faf6f0]'}`}>
                <div className="min-w-0 flex items-center gap-3">
                  <span className="w-9 h-9 shrink-0 rounded-full bg-[#1a1410] text-[#c9a876] flex items-center justify-center text-xs font-medium">{(u.fullName || '?').charAt(0).toUpperCase()}</span>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className="text-[#1a1410] font-medium truncate">{u.fullName || '(no name)'}</p>
                      {u.isBanned && <span className="text-[10px] tracking-[0.15em] uppercase bg-red-100 text-red-700 px-2 py-0.5 rounded">Suspended</span>}
                      {(u.favorites?.length || 0) > 0 && <span className="text-[10px] text-[#8b6b4f]">♥ {u.favorites.length}</span>}
                    </div>
                    <p className="text-xs text-[#8b6b4f] truncate">{u.email} · joined {u.createdAt ? new Date(u.createdAt).toLocaleDateString() : ''}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  {u.isBanned ? (
                    <button onClick={() => setBanned(u, false)} className="text-xs px-3 py-1.5 border border-green-300 text-green-700 rounded-lg hover:bg-green-50 inline-flex items-center gap-1"><UserCheck className="w-3 h-3" /> Restore</button>
                  ) : (
                    <button onClick={() => setBanned(u, true)} className="text-xs px-3 py-1.5 border border-amber-300 text-amber-700 rounded-lg hover:bg-amber-50 inline-flex items-center gap-1"><UserX className="w-3 h-3" /> Suspend</button>
                  )}
                  <button onClick={() => remove(u)} className="text-xs px-3 py-1.5 border border-red-300 text-red-700 rounded-lg hover:bg-red-50 inline-flex items-center gap-1"><Trash2 className="w-3 h-3" /> Delete</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
