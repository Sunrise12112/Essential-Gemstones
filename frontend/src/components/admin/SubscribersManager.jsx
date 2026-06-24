import React, { useEffect, useState } from 'react';
import { Trash2, RefreshCw, Download, Send } from 'lucide-react';
import api from '../../lib/api';
import { useToast } from '../../hooks/use-toast';

export default function SubscribersManager({ isSuper }) {
  const [subs, setSubs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [testEmail, setTestEmail] = useState('');
  const [sendingTest, setSendingTest] = useState(false);
  const { toast } = useToast();

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get('/admin/subscribers');
      setSubs(data);
    } catch (e) {
      toast({ title: 'Failed to load subscribers', description: e?.response?.data?.detail || e.message, variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, []);

  const remove = async (s) => {
    if (!window.confirm(`Remove ${s.email}?`)) return;
    try {
      await api.delete(`/admin/subscribers/${s.id}`);
      toast({ title: 'Removed', description: s.email });
      load();
    } catch (e) {
      toast({ title: 'Delete failed', description: e?.response?.data?.detail || e.message, variant: 'destructive' });
    }
  };

  const exportCsv = () => {
    if (subs.length === 0) return;
    const rows = [['email', 'createdAt'], ...subs.map((s) => [s.email, s.createdAt])];
    const csv = rows.map((r) => r.map((v) => `"${String(v ?? '').replace(/"/g, '""')}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `subscribers-${new Date().toISOString().slice(0,10)}.csv`;
    document.body.appendChild(a); a.click(); a.remove();
    URL.revokeObjectURL(url);
  };

  const sendTest = async () => {
    if (!testEmail) return;
    setSendingTest(true);
    try {
      await api.post('/admin/test-email', { to: testEmail });
      toast({ title: 'Test sent', description: `If credentials are correct, ${testEmail} will receive it shortly.` });
    } catch (e) {
      toast({ title: 'Test failed', description: e?.response?.data?.detail || e.message, variant: 'destructive' });
    } finally {
      setSendingTest(false);
    }
  };

  return (
    <div className="space-y-5">
      <p className="text-sm text-[#5a4a3d]">When someone submits the newsletter form, they appear here. Notification emails are sent to the address set in the <strong>Footer &amp; Contact</strong> section. Subscribers also receive a welcome email.</p>

      {isSuper && (
        <div className="border border-[#e8dfd1] rounded-2xl p-4 bg-[#faf6f0]">
          <p className="text-xs tracking-[0.2em] uppercase text-[#8b6b4f] mb-2">SMTP test</p>
          <div className="flex flex-col sm:flex-row gap-2">
            <input value={testEmail} onChange={(e) => setTestEmail(e.target.value)} placeholder="send-test-to@example.com" className="flex-1 px-4 py-2.5 border border-[#e8dfd1] rounded-lg focus:border-[#6b4f3a] focus:outline-none text-sm bg-white" />
            <button onClick={sendTest} disabled={sendingTest || !testEmail} className="inline-flex items-center justify-center gap-2 px-4 py-2.5 text-sm bg-[#1a1410] text-[#faf6f0] rounded-lg hover:bg-[#6b4f3a] disabled:opacity-60">
              {sendingTest ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />} Send test
            </button>
          </div>
        </div>
      )}

      <div className="flex items-center justify-between">
        <h4 className="font-serif text-lg text-[#1a1410]">{subs.length} subscriber{subs.length === 1 ? '' : 's'}</h4>
        <div className="flex items-center gap-2">
          <button onClick={load} className="inline-flex items-center gap-2 px-3 py-1.5 text-xs border border-[#e8dfd1] rounded-lg hover:bg-[#faf6f0]"><RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} /> Refresh</button>
          <button onClick={exportCsv} disabled={subs.length === 0} className="inline-flex items-center gap-2 px-3 py-1.5 text-xs border border-[#e8dfd1] rounded-lg hover:bg-[#faf6f0] disabled:opacity-50"><Download className="w-3 h-3" /> Export CSV</button>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center gap-2 text-sm text-[#6b4f3a]"><RefreshCw className="w-4 h-4 animate-spin" /> Loading…</div>
      ) : subs.length === 0 ? (
        <p className="text-sm text-[#8b6b4f] italic py-8 text-center border border-dashed border-[#e8dfd1] rounded-2xl">No subscribers yet. Share your site to start growing your list.</p>
      ) : (
        <div className="border border-[#e8dfd1] rounded-2xl overflow-hidden divide-y divide-[#e8dfd1]">
          {subs.map((s) => (
            <div key={s.id} className="flex items-center justify-between gap-3 px-5 py-3 bg-white hover:bg-[#faf6f0]">
              <div className="min-w-0">
                <p className="text-[#1a1410] font-medium truncate">{s.email}</p>
                <p className="text-xs text-[#8b6b4f]">{s.createdAt ? new Date(s.createdAt).toLocaleString() : ''}</p>
              </div>
              <button onClick={() => remove(s)} className="text-xs px-3 py-1.5 border border-red-300 text-red-700 rounded-lg hover:bg-red-50 inline-flex items-center gap-1 shrink-0"><Trash2 className="w-3 h-3" /> Remove</button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
