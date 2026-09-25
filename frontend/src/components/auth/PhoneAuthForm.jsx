import React, { useEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';
import api from '../../lib/api';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../hooks/use-toast';

const inputCls = 'w-full px-4 py-3 border border-[#e8dfd1] rounded-full focus:border-[#6b4f3a] focus:outline-none bg-white';
const labelCls = 'block text-xs tracking-[0.2em] uppercase text-[#8b6b4f] mb-2';

export default function PhoneAuthForm({ mode, onDone }) {
  const { sendPhoneCode, verifyPhoneCode } = useAuth();
  const { toast } = useToast();
  const [carriers, setCarriers] = useState([]);
  const [form, setForm] = useState({ fullName: '', phone: '', carrier: '', code: '' });
  const [stage, setStage] = useState('phone');
  const [sentTo, setSentTo] = useState('');
  const [cooldown, setCooldown] = useState(0);
  const [busy, setBusy] = useState(false);

  useEffect(() => { api.get('/sms/carriers').then((r) => setCarriers(r.data || [])).catch(() => {}); }, []);
  useEffect(() => {
    if (cooldown <= 0) return undefined;
    const id = setInterval(() => setCooldown((s) => Math.max(0, s - 1)), 1000);
    return () => clearInterval(id);
  }, [cooldown]);

  const send = async () => {
    setBusy(true);
    try {
      const data = await sendPhoneCode({ phone: form.phone, carrier: form.carrier });
      setSentTo(data.sentTo);
      setCooldown(data.resendAfterSeconds || 30);
      setStage('code');
      toast({ title: 'Code sent', description: `We texted a 6-digit code to ${data.sentTo}. It can take up to a minute to arrive.` });
    } catch (err) {
      toast({ title: 'Couldn\u2019t send code', description: String(err?.response?.data?.detail || 'Please try again.'), variant: 'destructive' });
    } finally { setBusy(false); }
  };

  const verify = async () => {
    setBusy(true);
    try {
      await verifyPhoneCode({ phone: form.phone, carrier: form.carrier, code: form.code, fullName: form.fullName });
      toast({ title: mode === 'register' ? 'Welcome to the family' : 'Signed in', description: 'You\u2019re in.' });
      onDone();
    } catch (err) {
      toast({ title: 'Wrong code', description: String(err?.response?.data?.detail || 'Please try again.'), variant: 'destructive' });
      setForm({ ...form, code: '' });
    } finally { setBusy(false); }
  };

  const onSubmit = (e) => { e.preventDefault(); if (stage === 'phone') send(); else verify(); };

  return (
    <form onSubmit={onSubmit} className="space-y-4" data-testid="phone-auth-form">
      {stage === 'phone' && (
        <>
          {mode === 'register' && (
            <div>
              <label className={labelCls}>Full name</label>
              <input required autoFocus value={form.fullName} onChange={(e) => setForm({ ...form, fullName: e.target.value })} placeholder="Your name" data-testid="phone-auth-name" className={inputCls} />
            </div>
          )}
          <div>
            <label className={labelCls}>Mobile number</label>
            <input type="tel" required autoFocus={mode !== 'register'} value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} placeholder="(555) 123-4567" data-testid="phone-auth-phone" className={inputCls} />
          </div>
          <div>
            <label className={labelCls}>Carrier</label>
            <select required value={form.carrier} onChange={(e) => setForm({ ...form, carrier: e.target.value })} data-testid="phone-auth-carrier" className={inputCls}>
              <option value="">Select your carrier</option>
              {carriers.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
            <p className="text-[11px] text-[#8b6b4f] mt-2">US &amp; Canada mobile numbers. Standard message rates may apply.</p>
          </div>
        </>
      )}
      {stage === 'code' && (
        <div>
          <label className={labelCls}>6-digit code sent to {sentTo}</label>
          <input inputMode="numeric" maxLength={6} required autoFocus value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value.replace(/\D/g, '').slice(0, 6) })} placeholder="000000" data-testid="phone-auth-code" className={`${inputCls} text-center tracking-[0.4em] text-lg`} />
          <div className="flex items-center justify-between mt-2">
            <button type="button" onClick={send} disabled={busy || cooldown > 0} data-testid="phone-auth-resend" className="text-xs text-[#6b4f3a] hover:text-[#1a1410] disabled:opacity-50">
              {cooldown > 0 ? `Resend in ${cooldown}s` : 'Resend code'}
            </button>
            <button type="button" onClick={() => setStage('phone')} data-testid="phone-auth-change-number" className="text-xs text-[#8b6b4f] hover:text-[#1a1410]">Change number</button>
          </div>
        </div>
      )}
      <button type="submit" disabled={busy || (stage === 'code' && form.code.length !== 6)} data-testid="phone-auth-submit" className="w-full py-3.5 bg-[#1a1410] text-[#faf6f0] rounded-full text-sm tracking-wider uppercase hover:bg-[#6b4f3a] transition-colors disabled:opacity-60 inline-flex items-center justify-center gap-2">
        {busy && <Loader2 className="w-4 h-4 animate-spin" />}
        {busy ? 'Please wait\u2026' : stage === 'phone' ? 'Text me a code' : (mode === 'register' ? 'Verify & create account' : 'Verify & sign in')}
      </button>
    </form>
  );
}
