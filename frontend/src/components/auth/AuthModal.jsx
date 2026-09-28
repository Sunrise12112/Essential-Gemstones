import React, { useState, useEffect } from 'react';
import { X, Loader2, Gem } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../hooks/use-toast';

export default function AuthModal() {
  const { authModalOpen, closeAuthModal, authModalMode, register, login, beginGoogleSignIn } = useAuth();
  const [mode, setMode] = useState(authModalMode);
  const [form, setForm] = useState({ fullName: '', email: '', password: '' });
  const [submitting, setSubmitting] = useState(false);
  const { toast } = useToast();

  useEffect(() => { setMode(authModalMode); }, [authModalMode]);

  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') closeAuthModal(); };
    if (authModalOpen) document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [authModalOpen, closeAuthModal]);

  if (!authModalOpen) return null;

  const onSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      if (mode === 'register') {
        await register({ fullName: form.fullName, email: form.email, password: form.password, subscribeNewsletter: true });
        toast({ title: 'Welcome to the family', description: 'Your account is ready. Check your inbox!' });
      } else {
        await login({ email: form.email, password: form.password });
        toast({ title: 'Signed in', description: 'Good to see you again.' });
      }
      setForm({ fullName: '', email: '', password: '' });
      closeAuthModal();
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Something went wrong. Please try again.';
      toast({ title: mode === 'register' ? 'Sign up failed' : 'Sign in failed', description: String(msg), variant: 'destructive' });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div role="dialog" aria-modal="true" aria-labelledby="auth-modal-heading" data-testid="auth-modal" className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-[#1a1410]/70 backdrop-blur-sm animate-in fade-in">
      <div onClick={closeAuthModal} data-testid="auth-modal-backdrop" className="absolute inset-0" />
      <div className="relative w-full max-w-md max-h-[90dvh] bg-[#faf6f0] rounded-3xl shadow-2xl overflow-y-auto">
        <button onClick={closeAuthModal} data-testid="auth-modal-close" className="absolute top-4 right-4 z-10 w-9 h-9 rounded-full bg-white/60 hover:bg-white flex items-center justify-center text-[#5a4a3d]" aria-label="Close">
          <X className="w-4 h-4" />
        </button>
        <div className="bg-[#2c2420] text-[#faf6f0] px-8 pt-9 pb-7">
          <div className="flex items-center gap-2 mb-2"><Gem className="w-5 h-5 text-[#c9a876]" /><span className="text-xs tracking-[0.3em] uppercase text-[#c9a876]">Essential Gemstones</span></div>
          <h2 id="auth-modal-heading" data-testid="auth-modal-title" className="font-serif text-3xl leading-tight mb-1">{mode === 'register' ? 'Join the family' : 'Welcome back'}</h2>
          <p className="text-sm text-[#d4c5af]">{mode === 'register' ? 'Create your account for member perks, favorites, and early access.' : 'Sign in to see your favorites and unlock member content.'}</p>
        </div>
        <div className="px-6 sm:px-8 py-7 space-y-4">
          <button
            type="button"
            onClick={beginGoogleSignIn}
            data-testid="auth-google-btn"
            className="w-full py-3 border border-[#e8dfd1] bg-white rounded-full text-sm text-[#1a1410] hover:bg-[#faf6f0] transition-colors inline-flex items-center justify-center gap-3"
          >
            <GoogleGlyph />
            Continue with Google
          </button>
          <div className="flex items-center gap-3 my-1">
            <div className="flex-1 h-px bg-[#e8dfd1]" />
            <span className="text-[10px] tracking-[0.2em] uppercase text-[#8b6b4f]">or</span>
            <div className="flex-1 h-px bg-[#e8dfd1]" />
          </div>
          <form onSubmit={onSubmit} data-testid="auth-email-form" className="space-y-4">
          {mode === 'register' && (
            <div>
              <label className="block text-xs tracking-[0.2em] uppercase text-[#8b6b4f] mb-2">Full name</label>
              <input required autoFocus data-testid="auth-email-name" value={form.fullName} onChange={(e) => setForm({ ...form, fullName: e.target.value })} placeholder="Your name" className="w-full px-4 py-3 border border-[#e8dfd1] rounded-full focus:border-[#6b4f3a] focus:outline-none bg-white" />
            </div>
          )}
          <div>
            <label className="block text-xs tracking-[0.2em] uppercase text-[#8b6b4f] mb-2">Email</label>
            <input type="email" required data-testid="auth-email-address" autoFocus={mode !== 'register'} value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="you@example.com" className="w-full px-4 py-3 border border-[#e8dfd1] rounded-full focus:border-[#6b4f3a] focus:outline-none bg-white" />
          </div>
          <div>
            <label className="block text-xs tracking-[0.2em] uppercase text-[#8b6b4f] mb-2">Password</label>
            <input type="password" required data-testid="auth-email-password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} placeholder={mode === 'register' ? '8+ characters, upper/lowercase, number, symbol' : ''} className="w-full px-4 py-3 border border-[#e8dfd1] rounded-full focus:border-[#6b4f3a] focus:outline-none bg-white" />
          </div>
          <button type="submit" disabled={submitting} data-testid="auth-email-submit" className="w-full py-3.5 bg-[#1a1410] text-[#faf6f0] rounded-full text-sm tracking-wider uppercase hover:bg-[#6b4f3a] transition-colors disabled:opacity-60 inline-flex items-center justify-center gap-2">
            {submitting && <Loader2 className="w-4 h-4 animate-spin" />}
            {submitting ? 'Please wait…' : mode === 'register' ? 'Create account' : 'Sign in'}
          </button>
          </form>
          <p className="text-center text-sm text-[#5a4a3d] pt-1">
            {mode === 'register' ? (
              <>Already have an account? <button type="button" data-testid="auth-switch-to-login" onClick={() => setMode('login')} className="text-[#6b4f3a] underline underline-offset-4">Sign in</button></>
            ) : (
              <>New here? <button type="button" data-testid="auth-switch-to-register" onClick={() => setMode('register')} className="text-[#6b4f3a] underline underline-offset-4">Create an account</button></>
            )}
          </p>
        </div>
      </div>
    </div>
  );
}

function GoogleGlyph() {
  return (
    <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true">
      <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
      <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
      <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
      <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
    </svg>
  );
}
