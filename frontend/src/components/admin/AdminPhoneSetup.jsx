import React, { useEffect, useState } from 'react';
import { MessageSquare, Trash2, Check } from 'lucide-react';
import api from '../../lib/api';
import { useToast } from '../../hooks/use-toast';

const inputCls = 'w-full min-w-0 px-4 py-2.5 border border-[#e8dfd1] rounded-xl focus:border-[#6b4f3a] focus:outline-none bg-white text-sm';
const buttonCls = 'px-4 py-2.5 rounded-xl text-sm disabled:opacity-60 transition-colors';

export default function AdminPhoneSetup({ me, onChange }) {
  const { toast } = useToast();
  const [phone, setPhone] = useState('');
  const [code, setCode] = useState('');
  const [sentTo, setSentTo] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [cooldown, setCooldown] = useState(0);

  useEffect(() => {
    if (cooldown <= 0) return undefined;
    const id = setInterval(() => setCooldown((s) => Math.max(0, s - 1)), 1000);
    return () => clearInterval(id);
  }, [cooldown]);

  const send = async (e) => {
    e?.preventDefault();
    if (busy) return;
    setBusy(true); setError('');
    try {
      const { data } = await api.put('/admin/me/phone', { phone });
      setSentTo(data.sentTo); setCode(''); setCooldown(data.resendAfterSeconds || 30);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Could not send a text. Please try again.');
    } finally { setBusy(false); }
  };

  const verify = async (e) => {
    e.preventDefault();
    if (busy) return;
    setBusy(true); setError('');
    try {
      const { data } = await api.post('/admin/me/phone/verify', { code });
      onChange(data.user);
      setSentTo(''); setCode(''); setPhone('');
      toast({ title: 'Phone verified', description: 'Text verification is now available when you sign in.' });
    } catch (err) {
      setError(err?.response?.data?.detail || 'Could not verify the code. Please try again.'); setCode('');
    } finally { setBusy(false); }
  };

  const remove = async () => {
    if (busy || !window.confirm('Remove your phone number? Text verification will no longer be offered at sign-in.')) return;
    setBusy(true); setError('');
    try {
      const { data } = await api.delete('/admin/me/phone');
      onChange(data.user); setSentTo(''); setCode(''); setPhone('');
      toast({ title: 'Phone removed' });
    } catch (err) { setError(err?.response?.data?.detail || 'Could not remove the number. Please try again.'); }
    finally { setBusy(false); }
  };

  return (
    <div className="space-y-4" data-testid="admin-phone-setup">
      <p data-testid="admin-phone-description" className="text-sm text-[#5a4a3d] -mt-1">Mobile and Google Voice numbers accepted. SMS delivery depends on your provider.</p>
      {me?.phone && (
        <div className="flex flex-wrap gap-3 items-center justify-between border border-[#e8dfd1] rounded-xl px-4 py-3 bg-[#faf6f0]" data-testid="admin-phone-current">
          <span data-testid="admin-phone-verified-number" className="inline-flex items-center gap-2 text-sm text-[#1a1410]"><Check className="w-4 h-4 text-green-700" /> {me.phone}</span>
          <button type="button" disabled={busy} onClick={remove} data-testid="admin-phone-remove" className="text-xs px-3 py-1.5 border border-[#e8dfd1] rounded-lg hover:bg-white inline-flex items-center gap-1 text-red-700 disabled:opacity-60"><Trash2 className="w-3 h-3" /> Remove</button>
        </div>
      )}
      {!sentTo ? (
        <form onSubmit={send} data-testid="admin-phone-number-form" className="grid sm:grid-cols-[minmax(0,1fr),auto] gap-3 items-end">
          <div className="min-w-0">
            <label htmlFor="admin-setup-phone" className="block text-xs tracking-[0.2em] uppercase text-[#8b6b4f] mb-1.5">{me?.phone ? 'New phone number' : 'Phone number'}</label>
            <input id="admin-setup-phone" type="tel" autoComplete="tel" required disabled={busy} value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+1 (415) 555-0123" data-testid="admin-phone-input" className={inputCls} />
          </div>
          <button type="submit" disabled={busy} data-testid="admin-phone-send" className={`${buttonCls} bg-[#1a1410] text-[#faf6f0] hover:bg-[#6b4f3a] inline-flex justify-center items-center gap-2`}><MessageSquare className="w-4 h-4 shrink-0" /> {busy ? 'Sending…' : 'Text me a code'}</button>
        </form>
      ) : (
        <form onSubmit={verify} data-testid="admin-phone-code-form" className="flex flex-wrap gap-3 items-end">
          <div className="w-full">
            <label htmlFor="admin-setup-code" data-testid="admin-phone-sent-to" className="block text-xs uppercase text-[#8b6b4f] mb-1.5">Code requested for {sentTo} · expires in 10 minutes</label>
            <input id="admin-setup-code" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} required autoFocus disabled={busy} value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))} placeholder="000000" data-testid="admin-phone-code" className={`${inputCls} max-w-48 text-center tracking-[0.4em]`} />
          </div>
          <button type="submit" disabled={busy || code.length !== 6} data-testid="admin-phone-verify" className={`${buttonCls} bg-[#1a1410] text-[#faf6f0] hover:bg-[#6b4f3a]`}>{busy ? 'Verifying…' : 'Verify'}</button>
          <button type="button" disabled={busy || cooldown > 0} onClick={() => send()} data-testid="admin-phone-resend" className={`${buttonCls} border border-[#e8dfd1] hover:bg-[#faf6f0]`}>{cooldown ? `Resend in ${cooldown}s` : 'Resend code'}</button>
          <button type="button" disabled={busy} onClick={() => { setSentTo(''); setCode(''); setError(''); }} data-testid="admin-phone-cancel" className={`${buttonCls} border border-[#e8dfd1] hover:bg-[#faf6f0]`}>Change number</button>
        </form>
      )}
      {error && <p role="alert" data-testid="admin-phone-error" className="text-sm text-red-800 break-words">{String(error)}</p>}
      <p data-testid="admin-phone-consent" className="text-xs text-[#8b6b4f]">Requesting a code authorizes a verification text. Message and data rates may apply.</p>
    </div>
  );
}