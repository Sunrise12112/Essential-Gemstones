import React, { useEffect, useState } from 'react';
import { Gem, X, Sparkles } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

const DISMISS_KEY = 'eg_signup_prompt_dismissed';
const DELAY_MS = 10000; // 10 seconds

export default function SignupPrompt() {
  const { user, openAuthModal, authModalOpen } = useAuth();
  const [show, setShow] = useState(false);

  useEffect(() => {
    if (user) return; // already logged in
    if (localStorage.getItem(DISMISS_KEY)) return; // previously dismissed
    const t = setTimeout(() => setShow(true), DELAY_MS);
    return () => clearTimeout(t);
  }, [user]);

  // Hide when user logs in / auth modal opens
  useEffect(() => { if (user || authModalOpen) setShow(false); }, [user, authModalOpen]);

  const dismiss = () => {
    localStorage.setItem(DISMISS_KEY, '1');
    setShow(false);
  };

  const join = () => {
    localStorage.setItem(DISMISS_KEY, '1');
    setShow(false);
    openAuthModal('register');
  };

  if (!show || user) return null;

  return (
    <div className="fixed inset-0 z-[90] flex items-end sm:items-center justify-center p-4 pointer-events-none">
      <div className="absolute inset-0 bg-[#1a1410]/40 backdrop-blur-sm pointer-events-auto animate-in fade-in" onClick={dismiss} />
      <div className="relative pointer-events-auto w-full max-w-md bg-[#faf6f0] rounded-3xl shadow-2xl overflow-hidden animate-in slide-in-from-bottom-6">
        <button onClick={dismiss} aria-label="Close" className="absolute top-4 right-4 z-10 w-9 h-9 rounded-full bg-white/60 hover:bg-white flex items-center justify-center text-[#5a4a3d]"><X className="w-4 h-4" /></button>
        <div className="bg-[#2c2420] text-[#faf6f0] px-8 pt-8 pb-6">
          <div className="flex items-center gap-2 mb-3"><Sparkles className="w-4 h-4 text-[#c9a876]" /><span className="text-xs tracking-[0.3em] uppercase text-[#c9a876]">Members Only</span></div>
          <h3 className="font-serif text-3xl md:text-4xl leading-tight mb-2">Become an Essential <span className="italic">member.</span></h3>
          <p className="text-sm text-[#d4c5af]">Save your favorite pieces, unlock member content, and be the first to know about new drops from Luca’s studio.</p>
        </div>
        <div className="px-8 py-6">
          <ul className="space-y-2 text-sm text-[#3d3128] mb-6">
            <li className="flex items-center gap-3"><Gem className="w-4 h-4 text-[#c9a876]" /> Save favorites & wishlist</li>
            <li className="flex items-center gap-3"><Gem className="w-4 h-4 text-[#c9a876]" /> Member-only content & perks</li>
            <li className="flex items-center gap-3"><Gem className="w-4 h-4 text-[#c9a876]" /> Early access to new collections</li>
          </ul>
          <button onClick={join} className="w-full py-3.5 bg-[#1a1410] text-[#faf6f0] rounded-full text-sm tracking-wider uppercase hover:bg-[#6b4f3a] transition-colors">Create free account</button>
          <button onClick={dismiss} className="w-full py-3 mt-2 text-sm text-[#8b6b4f] hover:text-[#3d3128]">Not now</button>
        </div>
      </div>
    </div>
  );
}
