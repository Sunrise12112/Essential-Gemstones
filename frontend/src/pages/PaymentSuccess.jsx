import React, { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { CheckCircle2, Loader2, XCircle, Gem, ArrowLeft } from 'lucide-react';
import api from '../lib/api';

const POLL_MAX = 6;

export default function PaymentSuccess() {
  const [params] = useSearchParams();
  const sessionId = params.get('session_id');
  const [state, setState] = useState('checking'); // checking | paid | pending | error
  const [info, setInfo] = useState(null);

  useEffect(() => {
    if (!sessionId) { setState('error'); return; }
    let attempts = 0;
    let cancelled = false;

    const poll = async () => {
      try {
        const { data } = await api.get(`/payments/status/${sessionId}`);
        if (cancelled) return;
        setInfo(data);
        if (data.payment_status === 'paid') { setState('paid'); return; }
        if (data.payment_status === 'expired' || data.status === 'expired') { setState('error'); return; }
        attempts += 1;
        if (attempts >= POLL_MAX) { setState('pending'); return; }
        setTimeout(poll, 2000);
      } catch (e) {
        if (cancelled) return;
        attempts += 1;
        if (attempts >= POLL_MAX) { setState('error'); return; }
        setTimeout(poll, 2000);
      }
    };
    poll();
    return () => { cancelled = true; };
  }, [sessionId]);

  const money = info?.amount ? `$${(info.amount / 100).toFixed(2)}` : '';

  return (
    <div className="min-h-screen bg-[#faf6f0] flex items-center justify-center px-6 py-16">
      <div data-testid="payment-success-card" className="w-full max-w-md bg-white rounded-3xl border border-[#e8dfd1] p-8 sm:p-10 shadow-xl text-center">
        <div className="flex items-center justify-center gap-2 mb-6 text-[#6b4f3a]">
          <Gem className="w-5 h-5" /><span className="font-serif text-lg text-[#2c2420]">Essential Gemstones</span>
        </div>

        {state === 'checking' && (
          <>
            <Loader2 className="w-12 h-12 text-[#6b4f3a] animate-spin mx-auto mb-5" />
            <h1 className="font-serif text-3xl text-[#1a1410] mb-2">Confirming your order…</h1>
            <p className="text-sm text-[#5a4a3d]">Hang tight while we verify your payment with Stripe.</p>
          </>
        )}

        {state === 'paid' && (
          <>
            <CheckCircle2 className="w-14 h-14 text-green-600 mx-auto mb-5" />
            <h1 data-testid="payment-success-title" className="font-serif text-3xl text-[#1a1410] mb-2">Thank you!</h1>
            <p className="text-sm text-[#5a4a3d] mb-1">Your payment {money && <span className="font-medium">of {money}</span>} was received.</p>
            {info?.product_name && <p className="text-sm text-[#5a4a3d] mb-6">{info.product_name} is on its way — we'll email you the details.</p>}
          </>
        )}

        {state === 'pending' && (
          <>
            <Loader2 className="w-12 h-12 text-[#6b4f3a] animate-spin mx-auto mb-5" />
            <h1 className="font-serif text-3xl text-[#1a1410] mb-2">Almost there</h1>
            <p className="text-sm text-[#5a4a3d] mb-6">Your payment is still processing. You'll get an email confirmation shortly.</p>
          </>
        )}

        {state === 'error' && (
          <>
            <XCircle className="w-14 h-14 text-[#c9483d] mx-auto mb-5" />
            <h1 className="font-serif text-3xl text-[#1a1410] mb-2">We couldn't confirm this</h1>
            <p className="text-sm text-[#5a4a3d] mb-6">If you were charged, don't worry — reach out and we'll sort it out right away.</p>
          </>
        )}

        <Link to="/" data-testid="payment-success-home" className="inline-flex items-center justify-center gap-2 px-6 py-3.5 bg-[#1a1410] text-[#faf6f0] rounded-full text-sm tracking-wider uppercase hover:bg-[#6b4f3a] transition-colors">
          <ArrowLeft className="w-4 h-4" /> Back to the shop
        </Link>
      </div>
    </div>
  );
}
