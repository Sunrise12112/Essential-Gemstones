import React from 'react';
import { Link } from 'react-router-dom';
import { Gem, ArrowLeft, ShoppingBag } from 'lucide-react';

export default function PaymentCancel() {
  return (
    <div className="min-h-screen bg-[#faf6f0] flex items-center justify-center px-6 py-16">
      <div data-testid="payment-cancel-card" className="w-full max-w-md bg-white rounded-3xl border border-[#e8dfd1] p-8 sm:p-10 shadow-xl text-center">
        <div className="flex items-center justify-center gap-2 mb-6 text-[#6b4f3a]">
          <Gem className="w-5 h-5" /><span className="font-serif text-lg text-[#2c2420]">Essential Gemstones</span>
        </div>
        <span className="w-14 h-14 rounded-full bg-[#f3ece0] flex items-center justify-center mx-auto mb-5">
          <ShoppingBag className="w-7 h-7 text-[#6b4f3a]" />
        </span>
        <h1 className="font-serif text-3xl text-[#1a1410] mb-2">No worries</h1>
        <p className="text-sm text-[#5a4a3d] mb-6">Your checkout was cancelled and you haven't been charged. Your favorite piece is still waiting whenever you're ready.</p>
        <Link to="/#shop" data-testid="payment-cancel-home" className="inline-flex items-center justify-center gap-2 px-6 py-3.5 bg-[#1a1410] text-[#faf6f0] rounded-full text-sm tracking-wider uppercase hover:bg-[#6b4f3a] transition-colors">
          <ArrowLeft className="w-4 h-4" /> Back to the shop
        </Link>
      </div>
    </div>
  );
}
