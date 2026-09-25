import React, { useEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../hooks/use-toast';

const inputCls = 'w-full min-w-0 px-4 py-3 border border-[#e8dfd1] rounded-full focus:border-[#6b4f3a] focus:outline-none bg-white';
const labelCls = 'block text-xs tracking-[0.2em] uppercase text-[#8b6b4f] mb-2';

export default function PhoneAuthForm({ mode, onDone }) {
  const { sendPhoneCode, verifyPhoneCode } = useAuth();
  const { toast } = useToast();
  const [phone, setPhone] = useState('');
  const [code, setCode] = useState('');
  const [stage, setStage] = useState('phone');
  const [sentTo, setSentTo] = useState('');
  const [cooldown, setCooldown] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (cooldown <= 0) return undefined;
    const id = setInterval(() => setCooldown((s) => Math.max(0, s - 1)), 1000);
    return () => clearInterval(id);
  }, [cooldown]);

  const send = async () => {
    if (busy) return;
    setBusy(true); setError('');
    try {
      const data = await sendPhoneCode({ phone });
      setSentTo(data.sentTo); setCode('');
      setCooldown(data.resendAfterSeconds || 30);
      setStage('code');
    } catch (err) {
      setError(String(err?.response?.data?.detail || 'Could not send a text. Please try another sign-in method.'));
    } finally { setBusy(false); }
  };

  const verify = async () => {
    if (busy) return;
    setBusy(true); setError('');
    try {
      await verifyPhoneCode({ phone, code });
      toast({ title: mode === 'register' ? 'Welcome to the family' : 'Signed in' });
      onDone();
    } catch (err) {
      setError(String(err?.response?.data?.detail || 'Could not verify the code. Please try again.'));
      setCode('');
    } finally { setBusy(false); }
  };

  return (
    <form onSubmit={(e) => { e.preventDefault(); stage === 'phone' ? send() : verify(); }} className="space-y-4" data-testid="phone-auth-form">
      {stage === 'phone' ? (
        <div>
          <label htmlFor="member-phone" className={labelCls}>Phone number</label>
          <input id="member-phone" type="tel" autoComplete="tel" required autoFocus disabled={busy} value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+1 (415) 555-0123" data-testid="phone-auth-phone" className={inputCls} aria-describedby="member-phone-hint" />
          <p id="member-phone-hint" data-testid="phone-auth-number-hint" className="text-xs text-[#8b6b4f] mt-2">Mobile or Google Voice. Include your country code outside the US or Canada.</p>
          <p data-testid="phone-auth-sms-consent" className="text-[11px] text-[#8b6b4f] mt-2">By continuing, you agree to receive a verification text. Message and data rates may apply.</p>
        </div>
      ) : (
        <div>
          <label htmlFor="member-phone-code" data-testid="phone-auth-sent-to" className={labelCls}>Code requested for {sentTo}</label>
          <p data-testid="phone-auth-delivery-status" className="text-xs text-[#8b6b4f] mb-3">Your code expires in 10 minutes. Delivery may take a moment.</p>
          <input id="member-phone-code" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} required autoFocus disabled={busy} value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))} placeholder="000000" data-testid="phone-auth-code" className={`${inputCls} text-center tracking-[0.4em] text-lg`} />
          <div className="flex flex-wrap gap-3 items-center justify-between mt-3">
            <button type="button" onClick={send} disabled={busy || cooldown > 0} data-testid="phone-auth-resend" className="text-xs text-[#6b4f3a] hover:text-[#1a1410] disabled:opacity-50">{cooldown > 0 ? `Resend in ${cooldown}s` : 'Resend code'}</button>
            <button type="button" disabled={busy} onClick={() => { setStage('phone'); setCode(''); setError(''); }} data-testid="phone-auth-change-number" className="text-xs text-[#8b6b4f] hover:text-[#1a1410] disabled:opacity-50">Change number</button>
          </div>
        </div>
      )}
      {error && <p role="alert" data-testid="phone-auth-error" className="text-sm text-red-800 break-words">{error}</p>}
      <button type="submit" disabled={busy || (stage === 'code' && code.length !== 6)} data-testid="phone-auth-submit" className="w-full py-3.5 px-3 bg-[#1a1410] text-[#faf6f0] rounded-full text-sm tracking-wider uppercase hover:bg-[#6b4f3a] transition-colors disabled:opacity-60 inline-flex items-center justify-center gap-2">
        {busy && <Loader2 className="w-4 h-4 animate-spin shrink-0" />}
        {busy ? 'Please wait…' : stage === 'phone' ? 'Text me a code' : (mode === 'register' ? 'Verify & create account' : 'Verify & sign in')}
      </button>
    </form>
  );
}