import React, { useEffect, useRef, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Loader2, Gem } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../hooks/use-toast';

// REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
export default function AuthCallback() {
  const { completeGoogleSignIn } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { toast } = useToast();
  const hasProcessed = useRef(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const hash = (location.hash || window.location.hash || '').replace(/^#/, '');
    const params = new URLSearchParams(hash);
    const sessionId = params.get('session_id');

    if (!sessionId) {
      navigate('/', { replace: true });
      return;
    }

    (async () => {
      try {
        const user = await completeGoogleSignIn(sessionId);
        // Clean the fragment before landing back on home
        window.history.replaceState(null, '', window.location.pathname);
        toast({ title: `Welcome, ${user?.fullName?.split(' ')[0] || 'friend'}`, description: 'Signed in with Google.' });
        navigate('/', { replace: true, state: { user } });
      } catch (e) {
        const msg = e?.response?.data?.detail || 'Something went wrong signing you in.';
        setError(String(msg));
        toast({ title: 'Google sign-in failed', description: String(msg), variant: 'destructive' });
      }
    })();
  }, [completeGoogleSignIn, location.hash, navigate, toast]);

  return (
    <div className="min-h-screen bg-[#faf6f0] flex items-center justify-center px-6">
      <div className="max-w-sm w-full text-center">
        <div className="inline-flex items-center gap-2 mb-3 text-[#6b4f3a]">
          <Gem className="w-5 h-5" />
          <span className="font-serif text-xl text-[#2c2420]">Essential Gemstones</span>
        </div>
        {error ? (
          <>
            <p className="text-sm text-[#c9483d] mb-4">{error}</p>
            <button
              onClick={() => { window.location.href = '/'; }}
              data-testid="auth-callback-back"
              className="text-xs tracking-wider uppercase px-4 py-2 rounded-full bg-[#1a1410] text-[#faf6f0] hover:bg-[#6b4f3a]"
            >
              Back to the site
            </button>
          </>
        ) : (
          <div className="inline-flex items-center gap-2 text-[#5a4a3d]" data-testid="auth-callback-loading">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span className="text-sm">Finishing sign-in…</span>
          </div>
        )}
      </div>
    </div>
  );
}
