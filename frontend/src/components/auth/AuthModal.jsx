import React, { useState, useEffect } from 'react';
import { X, Loader2, Gem, Phone } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../hooks/use-toast';

export default function AuthModal() {
  const { authModalOpen, closeAuthModal, authModalMode, register, login } = useAuth();
  const [mode, setMode] = useState(authModalMode);
  const [form, setForm] = useState({ fullName: '', email: '', phone: '', password: '' });
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
        await register({ fullName: form.fullName, email: form.email, phone: form.phone, password: form.password, subscribeNewsletter: true });
        toast({ title: 'Welcome to the family', description: 'Your account is ready. Check your inbox!' });
      } else {
        await login({ email: form.email, password: form.password });
        toast({ title: 'Signed in', description: 'Good to see you again.' });
      }
      setForm({ fullName: '', email: '', phone: '', password: '' });
      closeAuthModal();
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Something went wrong. Please try again.';
      toast({ title: mode === 'register' ? 'Sign up failed' : 'Sign in failed', description: String(msg), variant: 'destructive' });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-[#1a1410]/70 backdrop-blur-sm animate-in fade-in">
      <div onClick={closeAuthModal} className="absolute inset-0" />
      <div className="relative w-full max-w-md bg-[#faf6f0] rounded-3xl shadow-2xl overflow-hidden">
        <button onClick={closeAuthModal} className="absolute top-4 right-4 z-10 w-9 h-9 rounded-full bg-white/60 hover:bg-white flex items-center justify-center text-[#5a4a3d]" aria-label="Close">
          <X className="w-4 h-4" />
        </button>
        <div className="bg-[#2c2420] text-[#faf6f0] px-8 pt-9 pb-7">
          <div className="flex items-center gap-2 mb-2"><Gem className="w-5 h-5 text-[#c9a876]" /><span className="text-xs tracking-[0.3em] uppercase text-[#c9a876]">Essential Gemstones</span></div>
          <h2 className="font-serif text-3xl leading-tight mb-1">{mode === 'register' ? 'Join the family' : 'Welcome back'}</h2>
          <p className="text-sm text-[#d4c5af]">{mode === 'register' ? 'Create your account for member perks, favorites, and early access.' : 'Sign in to see your favorites and unlock member content.'}</p>
        </div>
        <form onSubmit={onSubmit} className="px-8 py-7 space-y-4">
          {mode === 'register' && (
            <>
              <div>
                <label className="block text-xs tracking-[0.2em] uppercase text-[#8b6b4f] mb-2">Full name</label>
                <input required autoFocus value={form.fullName} onChange={(e) => setForm({ ...form, fullName: e.target.value })} placeholder="Your name" data-testid="signup-full-name" className="w-full px-4 py-3 border border-[#e8dfd1] rounded-full focus:border-[#6b4f3a] focus:outline-none bg-white" />
              </div>
              <div>
                <label className="block text-xs tracking-[0.2em] uppercase text-[#8b6b4f] mb-2">Phone number</label>
                <div className="relative">
                  <Phone className="w-4 h-4 absolute left-4 top-1/2 -translate-y-1/2 text-[#8b6b4f]" />
                  <input
                    type="tel"
                    required
                    value={form.phone}
                    onChange={(e) => setForm({ ...form, phone: e.target.value })}
                    placeholder="+1 415 555 0100"
                    data-testid="signup-phone"
                    className="w-full pl-11 pr-4 py-3 border border-[#e8dfd1] rounded-full focus:border-[#6b4f3a] focus:outline-none bg-white"
                  />
                </div>
                <p className="text-[11px] text-[#8b6b4f] mt-1.5 pl-3">We'll only text you about your orders — never spam.</p>
              </div>
            </>
          )}
          <div>
            <label className="block text-xs tracking-[0.2em] uppercase text-[#8b6b4f] mb-2">Email</label>
            <input type="email" required autoFocus={mode !== 'register'} value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="you@example.com" data-testid="signup-email" className="w-full px-4 py-3 border border-[#e8dfd1] rounded-full focus:border-[#6b4f3a] focus:outline-none bg-white" />
          </div>
          <div>
            <label className="block text-xs tracking-[0.2em] uppercase text-[#8b6b4f] mb-2">Password</label>
            <input type="password" required value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} placeholder={mode === 'register' ? '8+ chars, incl. upper/lower/number/symbol' : ''} data-testid="signup-password" className="w-full px-4 py-3 border border-[#e8dfd1] rounded-full focus:border-[#6b4f3a] focus:outline-none bg-white" />
          </div>
          <button type="submit" disabled={submitting} data-testid="signup-submit" className="w-full py-3.5 bg-[#1a1410] text-[#faf6f0] rounded-full text-sm tracking-wider uppercase hover:bg-[#6b4f3a] transition-colors disabled:opacity-60 inline-flex items-center justify-center gap-2">
            {submitting && <Loader2 className="w-4 h-4 animate-spin" />}
            {submitting ? 'Please wait…' : mode === 'register' ? 'Create account' : 'Sign in'}
          </button>
          <p className="text-center text-sm text-[#5a4a3d] pt-1">
            {mode === 'register' ? (
              <>Already have an account? <button type="button" onClick={() => setMode('login')} className="text-[#6b4f3a] underline underline-offset-4">Sign in</button></>
            ) : (
              <>New here? <button type="button" onClick={() => setMode('register')} className="text-[#6b4f3a] underline underline-offset-4">Create an account</button></>
            )}
          </p>
        </form>
      </div>
    </div>
  );
}
