import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Lock, Gem, User, ShieldCheck, KeyRound, Copy, Check, RefreshCw, Smartphone } from 'lucide-react';
import api from '../lib/api';
import { useToast } from '../hooks/use-toast';

const PWD_MSG = 'Password must be at least 8 characters and include an uppercase letter, a lowercase letter, a number, and a symbol.';
const TRUST_TOKEN_KEY = 'eg_admin_trust_token';

function pwdIssues(p) {
  const list = [];
  if (!p || p.length < 8) list.push('At least 8 characters');
  if (!/[A-Z]/.test(p)) list.push('One uppercase letter');
  if (!/[a-z]/.test(p)) list.push('One lowercase letter');
  if (!/[0-9]/.test(p)) list.push('One number');
  if (!/[^A-Za-z0-9]/.test(p)) list.push('One symbol');
  return list;
}

export default function AdminLogin() {
  const [step, setStep] = useState('password'); // password | setup | choose | totp | sms | backup
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [setupToken, setSetupToken] = useState('');
  const [challengeToken, setChallengeToken] = useState('');
  const [, setPendingUser] = useState(null);
  const [setupData, setSetupData] = useState(null);
  const [availableMethods, setAvailableMethods] = useState(['totp']);
  const [phoneHint, setPhoneHint] = useState('');
  const [code, setCode] = useState('');
  const [backupCodes, setBackupCodes] = useState(null);
  const [copiedSecret, setCopiedSecret] = useState(false);
  const [trustDevice, setTrustDevice] = useState(false);
  const [smsSentAt, setSmsSentAt] = useState(0);
  const [resendCooldown, setResendCooldown] = useState(0);
  const codeRef = useRef(null);
  const navigate = useNavigate();
  const { toast } = useToast();

  useEffect(() => {
    if (localStorage.getItem('eg_admin_token')) navigate('/admin/dashboard');
  }, [navigate]);

  useEffect(() => {
    if ((step === 'totp' || step === 'sms' || step === 'backup' || (step === 'setup' && setupData)) && codeRef.current) {
      codeRef.current.focus();
    }
  }, [step, setupData]);

  // Countdown for SMS resend
  useEffect(() => {
    if (resendCooldown <= 0) return undefined;
    const id = setInterval(() => {
      setResendCooldown((s) => Math.max(0, s - 1));
    }, 1000);
    return () => clearInterval(id);
  }, [resendCooldown]);

  const submitPassword = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const trustToken = localStorage.getItem(TRUST_TOKEN_KEY) || '';
      const { data } = await api.post(
        '/admin/login',
        { username, password },
        trustToken ? { headers: { 'X-Admin-Trust-Token': trustToken } } : {},
      );
      if (data.status === 'ok' && data.token) {
        // Trusted device let us skip 2FA
        localStorage.setItem('eg_admin_token', data.token);
        if (data.user) localStorage.setItem('eg_admin_user', JSON.stringify(data.user));
        toast({ title: 'Welcome back', description: 'This device was trusted \u2014 skipped 2FA.' });
        navigate('/admin/dashboard');
        return;
      }
      if (data.status === 'needs_2fa') {
        setChallengeToken(data.twoFactorToken);
        setAvailableMethods(Array.isArray(data.availableMethods) && data.availableMethods.length ? data.availableMethods : ['totp']);
        setPhoneHint(data.phoneHint || '');
        // If only one method, jump straight to it
        if (!data.availableMethods || data.availableMethods.length <= 1) {
          setStep('totp');
        } else {
          setStep('choose');
        }
      } else if (data.status === 'needs_2fa_setup') {
        setSetupToken(data.setupToken);
        setPendingUser(data.user);
        const setupRes = await api.post('/admin/2fa/setup', {}, { headers: { Authorization: `Bearer ${data.setupToken}` } });
        setSetupData(setupRes.data);
        setStep('setup');
      } else if (data.token) {
        // Legacy path
        localStorage.setItem('eg_admin_token', data.token);
        if (data.user) localStorage.setItem('eg_admin_user', JSON.stringify(data.user));
        navigate('/admin/dashboard');
      }
    } catch (err) {
      // If the trusted-device token got rejected somehow, drop it
      if (err?.response?.status === 401) localStorage.removeItem(TRUST_TOKEN_KEY);
      toast({ title: 'Login failed', description: err?.response?.data?.detail || 'Incorrect username or password.', variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  };

  const submitEnable = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const { data } = await api.post('/admin/2fa/enable', { code }, { headers: { Authorization: `Bearer ${setupToken}` } });
      localStorage.setItem('eg_admin_token', data.token);
      if (data.user) localStorage.setItem('eg_admin_user', JSON.stringify(data.user));
      setBackupCodes(data.backupCodes || []);
    } catch (err) {
      toast({ title: 'Wrong code', description: err?.response?.data?.detail || 'Try the current 6-digit code from your authenticator.', variant: 'destructive' });
      setCode('');
    } finally {
      setLoading(false);
    }
  };

  const sendSmsCode = async () => {
    setLoading(true);
    try {
      const { data } = await api.post('/admin/2fa/sms/send', {}, { headers: { Authorization: `Bearer ${challengeToken}` } });
      setPhoneHint(data.sentTo || phoneHint);
      setSmsSentAt(Date.now());
      setResendCooldown(data.resendAfterSeconds || 30);
      toast({ title: 'Code sent', description: `We texted a 6-digit code to ${data.sentTo}. It expires in ${data.expiresInMinutes || 5} minutes.` });
    } catch (err) {
      toast({ title: 'Couldn\u2019t send code', description: err?.response?.data?.detail || 'Try your authenticator app instead.', variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  };

  const chooseMethod = async (method) => {
    setCode('');
    if (method === 'sms') {
      setStep('sms');
      await sendSmsCode();
    } else if (method === 'backup') {
      setStep('backup');
    } else {
      setStep('totp');
    }
  };

  const submitChallenge = async (e, method) => {
    e.preventDefault();
    setLoading(true);
    try {
      const { data } = await api.post(
        '/admin/2fa/login',
        { code, method, trustDevice },
        { headers: { Authorization: `Bearer ${challengeToken}` } },
      );
      localStorage.setItem('eg_admin_token', data.token);
      if (data.user) localStorage.setItem('eg_admin_user', JSON.stringify(data.user));
      if (data.trustDeviceToken) {
        localStorage.setItem(TRUST_TOKEN_KEY, data.trustDeviceToken);
        toast({ title: 'Device trusted', description: `You won\u2019t need a code on this device for ${data.trustDeviceDays || 30} days.` });
      }
      navigate('/admin/dashboard');
    } catch (err) {
      toast({ title: 'Wrong code', description: err?.response?.data?.detail || 'Try again with the current code.', variant: 'destructive' });
      setCode('');
    } finally {
      setLoading(false);
    }
  };

  const copySecret = async () => {
    try {
      await navigator.clipboard.writeText(setupData?.secret || '');
      setCopiedSecret(true);
      setTimeout(() => setCopiedSecret(false), 1500);
    } catch (e) { /* ignore */ }
  };

  const copyBackupCodes = async () => {
    try {
      await navigator.clipboard.writeText((backupCodes || []).join('\n'));
      toast({ title: 'Copied', description: '10 backup codes copied to your clipboard.' });
    } catch (e) { /* ignore */ }
  };

  const proceedAfterBackups = () => {
    navigate('/admin/dashboard');
  };

  const restart = () => {
    setStep('password');
    setCode('');
    setChallengeToken('');
    setTrustDevice(false);
  };

  return (
    <div className="min-h-screen bg-[#faf6f0] flex items-center justify-center px-6 py-10">
      {step === 'password' && (
        <LoginCard>
          <h1 className="font-serif text-3xl text-[#1a1410] mb-2">Admin Login</h1>
          <p className="text-sm text-[#5a4a3d] mb-8">Sign in to manage the site.</p>
          <form onSubmit={submitPassword}>
            <label className="block text-xs tracking-[0.2em] uppercase text-[#8b6b4f] mb-2">Username</label>
            <div className="relative mb-5">
              <User className="w-4 h-4 absolute left-4 top-1/2 -translate-y-1/2 text-[#8b6b4f]" />
              <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required autoFocus data-testid="admin-login-username" className="w-full pl-11 pr-4 py-3.5 border border-[#e8dfd1] rounded-full focus:border-[#6b4f3a] focus:outline-none bg-[#faf6f0]" placeholder="luca" />
            </div>
            <label className="block text-xs tracking-[0.2em] uppercase text-[#8b6b4f] mb-2">Password</label>
            <div className="relative mb-6">
              <Lock className="w-4 h-4 absolute left-4 top-1/2 -translate-y-1/2 text-[#8b6b4f]" />
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required autoComplete="current-password" data-testid="admin-login-password" className="w-full pl-11 pr-4 py-3.5 border border-[#e8dfd1] rounded-full focus:border-[#6b4f3a] focus:outline-none bg-[#faf6f0]" placeholder={'\u2022'.repeat(10)} />
            </div>
            <button type="submit" disabled={loading} data-testid="admin-login-submit" className="w-full py-3.5 bg-[#1a1410] text-[#faf6f0] rounded-full text-sm tracking-wider uppercase hover:bg-[#6b4f3a] transition-colors disabled:opacity-60">
              {loading ? 'Signing in\u2026' : 'Sign in'}
            </button>
          </form>
          <p className="mt-5 text-xs text-[#8b6b4f] text-center">Two-factor authentication is required for all admins.</p>
        </LoginCard>
      )}

      {step === 'setup' && !backupCodes && setupData && (
        <div className="w-full max-w-xl bg-white rounded-3xl border border-[#e8dfd1] p-8 sm:p-10 shadow-xl" data-testid="admin-2fa-setup">
          <div className="flex items-center gap-2 mb-1 text-[#6b4f3a]">
            <ShieldCheck className="w-5 h-5" />
            <span className="text-xs tracking-[0.2em] uppercase">Set up two-factor authentication</span>
          </div>
          <h1 className="font-serif text-3xl text-[#1a1410] mb-1">One-time setup</h1>
          <p className="text-sm text-[#5a4a3d] mb-5">Scan this QR with Microsoft Authenticator (or any authenticator app). Then enter the 6-digit code it shows to finish.</p>
          <div className="grid sm:grid-cols-[220px,1fr] gap-6 items-start">
            <div className="p-3 bg-white border border-[#e8dfd1] rounded-2xl inline-block">
              <img src={setupData.qrDataUrl} alt="Two factor QR" className="w-[196px] h-[196px]" data-testid="admin-2fa-qr" />
            </div>
            <div>
              <p className="text-xs tracking-[0.2em] uppercase text-[#8b6b4f] mb-1">Can&apos;t scan? Enter this key manually</p>
              <div className="flex items-center gap-2 mb-4">
                <code className="flex-1 text-xs bg-[#faf6f0] border border-[#e8dfd1] rounded-lg px-3 py-2 break-all font-mono" data-testid="admin-2fa-secret">{setupData.secret}</code>
                <button type="button" onClick={copySecret} aria-label="Copy secret" className="w-9 h-9 rounded-full border border-[#e8dfd1] hover:bg-[#faf6f0] flex items-center justify-center">
                  {copiedSecret ? <Check className="w-4 h-4 text-green-700" /> : <Copy className="w-4 h-4 text-[#6b4f3a]" />}
                </button>
              </div>
              <p className="text-[11px] text-[#8b6b4f]">Account: <span className="text-[#3d3128]">{setupData.accountName}</span> \u00b7 Issuer: <span className="text-[#3d3128]">{setupData.issuer}</span></p>
              <p className="text-[11px] text-[#8b6b4f]">6-digit codes \u00b7 SHA1 \u00b7 30-second period (RFC 6238).</p>
            </div>
          </div>
          <form onSubmit={submitEnable} className="mt-6">
            <label className="block text-xs tracking-[0.2em] uppercase text-[#8b6b4f] mb-2">Enter the 6-digit code from your app</label>
            <div className="relative mb-5">
              <KeyRound className="w-4 h-4 absolute left-4 top-1/2 -translate-y-1/2 text-[#8b6b4f]" />
              <input
                ref={codeRef}
                inputMode="numeric"
                pattern="[0-9]{6}"
                maxLength={6}
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                data-testid="admin-2fa-setup-code"
                className="w-full pl-11 pr-4 py-3.5 border border-[#e8dfd1] rounded-full focus:border-[#6b4f3a] focus:outline-none bg-[#faf6f0] tracking-[0.4em] text-center text-lg"
                placeholder="000000"
                required
              />
            </div>
            <button type="submit" disabled={loading || code.length !== 6} data-testid="admin-2fa-setup-submit" className="w-full py-3.5 bg-[#1a1410] text-[#faf6f0] rounded-full text-sm tracking-wider uppercase hover:bg-[#6b4f3a] transition-colors disabled:opacity-60">
              {loading ? <span className="inline-flex items-center gap-2"><RefreshCw className="w-4 h-4 animate-spin" /> Verifying\u2026</span> : 'Enable 2FA'}
            </button>
          </form>
        </div>
      )}

      {step === 'setup' && backupCodes && (
        <div className="w-full max-w-lg bg-white rounded-3xl border border-[#e8dfd1] p-8 sm:p-10 shadow-xl" data-testid="admin-2fa-backup">
          <div className="flex items-center gap-2 mb-1 text-[#6b4f3a]">
            <KeyRound className="w-5 h-5" />
            <span className="text-xs tracking-[0.2em] uppercase">Save your backup codes</span>
          </div>
          <h1 className="font-serif text-3xl text-[#1a1410] mb-2">Keep these somewhere safe</h1>
          <p className="text-sm text-[#5a4a3d] mb-5">Each code works once and lets you sign in if you lose access to your authenticator app. Save them in a password manager or print them.</p>
          <div className="grid grid-cols-2 gap-2 mb-5 font-mono text-sm">
            {backupCodes.map((c) => (
              <div key={c} className="bg-[#faf6f0] border border-[#e8dfd1] rounded-lg px-3 py-2 text-center text-[#3d3128] tracking-wider" data-testid="admin-2fa-backup-code">{c}</div>
            ))}
          </div>
          <div className="flex gap-2">
            <button type="button" onClick={copyBackupCodes} className="flex-1 py-3 border border-[#e8dfd1] rounded-full text-sm hover:bg-[#faf6f0] inline-flex items-center justify-center gap-2"><Copy className="w-4 h-4" /> Copy all</button>
            <button type="button" onClick={proceedAfterBackups} data-testid="admin-2fa-backup-continue" className="flex-1 py-3 bg-[#1a1410] text-[#faf6f0] rounded-full text-sm tracking-wider uppercase hover:bg-[#6b4f3a]">I&apos;ve saved them</button>
          </div>
        </div>
      )}

      {step === 'choose' && (
        <LoginCard>
          <div className="flex items-center gap-2 mb-1 text-[#6b4f3a]">
            <ShieldCheck className="w-5 h-5" />
            <span className="text-xs tracking-[0.2em] uppercase">Two-factor authentication</span>
          </div>
          <h1 className="font-serif text-3xl text-[#1a1410] mb-2">How would you like to sign in?</h1>
          <p className="text-sm text-[#5a4a3d] mb-6">Pick a method to receive your 6-digit code.</p>
          <div className="space-y-3">
            <MethodButton
              testid="admin-2fa-choose-totp"
              icon={<Smartphone className="w-5 h-5" />}
              title="Use my authenticator app"
              sub="Open Microsoft Authenticator (or similar) and enter the 6-digit code."
              onClick={() => chooseMethod('totp')}
            />
            {availableMethods.includes('sms') && (
              <MethodButton
                testid="admin-2fa-choose-sms"
                icon={<Smartphone className="w-5 h-5" />}
                title="Text me a code"
                sub={phoneHint ? `Send a 6-digit code by SMS to ${phoneHint}.` : 'Send a 6-digit code to your admin phone.'}
                onClick={() => chooseMethod('sms')}
              />
            )}
            <MethodButton
              testid="admin-2fa-choose-backup"
              icon={<KeyRound className="w-5 h-5" />}
              title="Use a backup code"
              sub="Enter one of the 10 recovery codes you saved when you set up 2FA."
              onClick={() => chooseMethod('backup')}
            />
          </div>
          <button type="button" onClick={restart} className="w-full mt-6 text-xs text-[#8b6b4f] hover:text-[#1a1410]" data-testid="admin-2fa-choose-cancel">Use a different account</button>
        </LoginCard>
      )}

      {step === 'totp' && (
        <ChallengeCard
          title="Enter your code"
          hint="Open your authenticator app and enter the current 6-digit code for Essential Gemstones."
          canSwitch={availableMethods.length > 1 || true}
          onSwitch={() => setStep('choose')}
          onCancel={restart}
        >
          <form onSubmit={(e) => submitChallenge(e, 'totp')} data-testid="admin-2fa-challenge">
            <CodeInput
              value={code}
              onChange={(v) => setCode(v.replace(/\D/g, '').slice(0, 6))}
              refEl={codeRef}
              testid="admin-2fa-challenge-code"
              placeholder="000000"
              maxLength={6}
            />
            <TrustToggle trustDevice={trustDevice} setTrustDevice={setTrustDevice} />
            <button type="submit" disabled={loading || code.length < 6} data-testid="admin-2fa-challenge-submit" className="w-full py-3.5 bg-[#1a1410] text-[#faf6f0] rounded-full text-sm tracking-wider uppercase hover:bg-[#6b4f3a] transition-colors disabled:opacity-60">
              {loading ? 'Verifying\u2026' : 'Verify & sign in'}
            </button>
          </form>
        </ChallengeCard>
      )}

      {step === 'sms' && (
        <ChallengeCard
          title="Check your phone"
          hint={`We texted a 6-digit code to ${phoneHint || 'your admin phone'}. It expires in 5 minutes.`}
          canSwitch
          onSwitch={() => setStep('choose')}
          onCancel={restart}
        >
          <form onSubmit={(e) => submitChallenge(e, 'sms')} data-testid="admin-2fa-sms-form">
            <CodeInput
              value={code}
              onChange={(v) => setCode(v.replace(/\D/g, '').slice(0, 6))}
              refEl={codeRef}
              testid="admin-2fa-sms-code"
              placeholder="000000"
              maxLength={6}
            />
            <div className="flex items-center justify-between mb-4">
              <button
                type="button"
                onClick={sendSmsCode}
                disabled={loading || resendCooldown > 0}
                data-testid="admin-2fa-sms-resend"
                className="text-xs text-[#6b4f3a] hover:text-[#1a1410] disabled:opacity-50"
              >
                {resendCooldown > 0 ? `Resend in ${resendCooldown}s` : (smsSentAt ? 'Resend code' : 'Send code')}
              </button>
              <span className="text-[11px] text-[#8b6b4f]">Standard message rates may apply.</span>
            </div>
            <TrustToggle trustDevice={trustDevice} setTrustDevice={setTrustDevice} />
            <button type="submit" disabled={loading || code.length !== 6} data-testid="admin-2fa-sms-submit" className="w-full py-3.5 bg-[#1a1410] text-[#faf6f0] rounded-full text-sm tracking-wider uppercase hover:bg-[#6b4f3a] transition-colors disabled:opacity-60">
              {loading ? 'Verifying\u2026' : 'Verify & sign in'}
            </button>
          </form>
        </ChallengeCard>
      )}

      {step === 'backup' && (
        <ChallengeCard
          title="Enter a backup code"
          hint="Use one of the 10 recovery codes you saved when you enabled 2FA. Each code works only once."
          canSwitch
          onSwitch={() => setStep('choose')}
          onCancel={restart}
        >
          <form onSubmit={(e) => submitChallenge(e, 'backup')} data-testid="admin-2fa-backup-form">
            <CodeInput
              value={code}
              onChange={(v) => setCode(v.toUpperCase().slice(0, 12))}
              refEl={codeRef}
              testid="admin-2fa-backup-input"
              placeholder="XXXX-XXXX"
              maxLength={12}
              upper
            />
            <TrustToggle trustDevice={trustDevice} setTrustDevice={setTrustDevice} />
            <button type="submit" disabled={loading || code.length < 8} data-testid="admin-2fa-backup-submit" className="w-full py-3.5 bg-[#1a1410] text-[#faf6f0] rounded-full text-sm tracking-wider uppercase hover:bg-[#6b4f3a] transition-colors disabled:opacity-60">
              {loading ? 'Verifying\u2026' : 'Verify & sign in'}
            </button>
          </form>
        </ChallengeCard>
      )}
    </div>
  );
}

export { pwdIssues, PWD_MSG };

function LoginCard({ children }) {
  return (
    <div className="w-full max-w-md bg-white rounded-3xl border border-[#e8dfd1] p-8 sm:p-10 shadow-xl">
      <div className="flex items-center gap-2 mb-2 text-[#6b4f3a]">
        <Gem className="w-5 h-5" />
        <span className="font-serif text-xl text-[#2c2420]">Essential Gemstones</span>
      </div>
      {children}
    </div>
  );
}

function ChallengeCard({ title, hint, children, canSwitch, onSwitch, onCancel }) {
  return (
    <LoginCard>
      <div className="flex items-center gap-2 mb-1 text-[#6b4f3a]">
        <ShieldCheck className="w-5 h-5" />
        <span className="text-xs tracking-[0.2em] uppercase">Two-factor authentication</span>
      </div>
      <h1 data-testid="admin-challenge-title" className="font-serif text-3xl text-[#1a1410] mb-2">{title}</h1>
      <p data-testid="admin-challenge-hint" className="text-sm text-[#5a4a3d] mb-6">{hint}</p>
      {children}
      <div className="flex items-center justify-between mt-4">
        {canSwitch ? (
          <button type="button" onClick={onSwitch} data-testid="admin-2fa-switch-method" className="text-xs text-[#6b4f3a] hover:text-[#1a1410]">Use a different method</button>
        ) : <span />}
        <button type="button" onClick={onCancel} data-testid="admin-challenge-change-account" className="text-xs text-[#8b6b4f] hover:text-[#1a1410]">Use a different account</button>
      </div>
    </LoginCard>
  );
}

function CodeInput({ value, onChange, refEl, testid, placeholder, maxLength, upper }) {
  return (
    <div className="relative mb-4">
      <KeyRound className="w-4 h-4 absolute left-4 top-1/2 -translate-y-1/2 text-[#8b6b4f]" />
      <input
        ref={refEl}
        inputMode={upper ? 'text' : 'numeric'}
        autoComplete={upper ? 'off' : 'one-time-code'}
        maxLength={maxLength}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        data-testid={testid}
        className={`w-full pl-11 pr-4 py-3.5 border border-[#e8dfd1] rounded-full focus:border-[#6b4f3a] focus:outline-none bg-[#faf6f0] text-center text-lg ${upper ? 'tracking-[0.3em]' : 'tracking-[0.4em]'}`}
        placeholder={placeholder}
        required
        autoFocus
      />
    </div>
  );
}

function TrustToggle({ trustDevice, setTrustDevice }) {
  return (
    <label className="flex items-start gap-2 mb-5 cursor-pointer select-none" data-testid="admin-2fa-trust-toggle-label">
      <input
        type="checkbox"
        checked={trustDevice}
        onChange={(e) => setTrustDevice(e.target.checked)}
        className="mt-1 accent-[#6b4f3a]"
        data-testid="admin-2fa-trust-checkbox"
      />
      <span className="text-xs text-[#5a4a3d] leading-relaxed">
        <span className="text-[#3d3128] font-medium">Trust this device for 30 days.</span>{' '}
        Skip 2FA on this browser until it expires. Only tick this on your own computer.
      </span>
    </label>
  );
}

function MethodButton({ icon, title, sub, onClick, testid }) {
  return (
    <button
      type="button"
      onClick={onClick}
      data-testid={testid}
      className="w-full flex items-start gap-3 p-4 border border-[#e8dfd1] rounded-2xl text-left hover:bg-[#faf6f0] transition-colors group"
    >
      <span className="w-10 h-10 rounded-full bg-[#faf6f0] border border-[#e8dfd1] flex items-center justify-center text-[#6b4f3a] group-hover:bg-white">
        {icon}
      </span>
      <span className="flex-1">
        <span className="block text-sm text-[#1a1410] font-medium">{title}</span>
        <span className="block text-xs text-[#8b6b4f] mt-0.5">{sub}</span>
      </span>
    </button>
  );
}
