import React, { useEffect, useState } from 'react';
import { MessageSquare, Trash2, Check } from 'lucide-react';
import api from '../../lib/api';
import { useToast } from '../../hooks/use-toast';

const inputCls = 'w-full px-4 py-2.5 border border-[#e8dfd1] rounded-xl focus:border-[#6b4f3a] focus:outline-none bg-white text-sm';

export default function AdminPhoneSetup({ me, onChange }) {
  const { toast } = useToast();
  const [carriers, setCarriers] = useState([]);
  const [phone, setPhone] = useState('');
  const [carrier, setCarrier] = useState('');
  const [code, setCode] = useState('');
  const [sentTo, setSentTo] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => { api.get('/sms/carriers').then((r) => setCarriers(r.data || [])).catch(() => {}); }, []);

  const send = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const { data } = await api.put('/admin/me/phone', { phone, carrier });
      setSentTo(data.sentTo);
      toast({ title: 'Code sent', description: `We texted a verification code to ${data.sentTo}.` });
    } catch (err) {
      toast({ title: 'Couldn\u2019t send code', description: err?.response?.data?.detail || 'Try again.', variant: 'destructive' });
    } finally { setBusy(false); }
  };

  const verify = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const { data } = await api.post('/admin/me/phone/verify', { code });
      onChange(data.user);
      setSentTo(''); setCode(''); setPhone('');
      toast({ title: 'Phone verified', description: '"Text me a code" is now available when you sign in.' });
    } catch (err) {
      toast({ title: 'Wrong code', description: err?.response?.data?.detail || 'Try again.', variant: 'destructive' });
      setCode('');
    } finally { setBusy(false); }
  };

  const remove = async () => {
    if (!window.confirm('Remove your phone number? SMS codes will no longer be offered at sign-in.')) return;
    const { data } = await api.delete('/admin/me/phone');
    onChange(data.user);
    toast({ title: 'Phone removed' });
  };

  return (
    <div className="space-y-4" data-testid="admin-phone-setup">
      <p className="text-sm text-[#5a4a3d] -mt-1">Add a mobile number to receive sign-in codes by text. Codes are delivered through your carrier&apos;s free text gateway (US &amp; Canada).</p>
      {me?.phone && (
        <div className="flex items-center justify-between border border-[#e8dfd1] rounded-xl px-4 py-3 bg-[#faf6f0]" data-testid="admin-phone-current">
          <span className="inline-flex items-center gap-2 text-sm text-[#1a1410]"><Check className="w-4 h-4 text-green-700" /> {me.phone} <span className="text-xs text-[#8b6b4f]">({carriers.find((c) => c.id === me.phoneCarrier)?.name || me.phoneCarrier})</span></span>
          <button type="button" onClick={remove} data-testid="admin-phone-remove" className="text-xs px-3 py-1.5 border border-[#e8dfd1] rounded-lg hover:bg-white inline-flex items-center gap-1 text-red-700"><Trash2 className="w-3 h-3" /> Remove</button>
        </div>
      )}
      {!sentTo ? (
        <form onSubmit={send} className="grid sm:grid-cols-[1fr,1fr,auto] gap-3 items-end">
          <div>
            <label className="block text-xs tracking-[0.2em] uppercase text-[#8b6b4f] mb-1.5">{me?.phone ? 'New mobile number' : 'Mobile number'}</label>
            <input type="tel" required value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="(555) 123-4567" data-testid="admin-phone-input" className={inputCls} />
          </div>
          <div>
            <label className="block text-xs tracking-[0.2em] uppercase text-[#8b6b4f] mb-1.5">Carrier</label>
            <select required value={carrier} onChange={(e) => setCarrier(e.target.value)} data-testid="admin-phone-carrier" className={inputCls}>
              <option value="">Select carrier</option>
              {carriers.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
          <button type="submit" disabled={busy} data-testid="admin-phone-send" className="px-4 py-2.5 bg-[#1a1410] text-[#faf6f0] rounded-xl text-sm hover:bg-[#6b4f3a] disabled:opacity-60 inline-flex items-center gap-2"><MessageSquare className="w-4 h-4" /> {busy ? 'Sending\u2026' : 'Text me a code'}</button>
        </form>
      ) : (
        <form onSubmit={verify} className="flex flex-wrap gap-3 items-end">
          <div>
            <label className="block text-xs tracking-[0.2em] uppercase text-[#8b6b4f] mb-1.5">Code sent to {sentTo}</label>
            <input inputMode="numeric" maxLength={6} required value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))} placeholder="000000" data-testid="admin-phone-code" className={`${inputCls} w-40 text-center tracking-[0.4em]`} />
          </div>
          <button type="submit" disabled={busy || code.length !== 6} data-testid="admin-phone-verify" className="px-4 py-2.5 bg-[#1a1410] text-[#faf6f0] rounded-xl text-sm hover:bg-[#6b4f3a] disabled:opacity-60">{busy ? 'Verifying\u2026' : 'Verify'}</button>
          <button type="button" onClick={() => setSentTo('')} data-testid="admin-phone-cancel" className="px-4 py-2.5 border border-[#e8dfd1] rounded-xl text-sm hover:bg-[#faf6f0]">Cancel</button>
        </form>
      )}
    </div>
  );
}
