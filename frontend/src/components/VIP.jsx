import React from 'react';
import { Crown, Gift, Star, MessageCircle, Heart, Sparkles, Gem, Lock } from 'lucide-react';
import { useSite } from '../context/SiteContext';
import { useAuth } from '../context/AuthContext';

const ICONS = { Gift, Star, MessageCircle, Heart, Sparkles, Gem, Crown };

export default function VIP() {
  const { site } = useSite();
  const { user, openAuthModal } = useAuth();
  const v = site.vip || {};
  const perks = v.perks || [];

  return (
    <section id="members" className="py-24 md:py-32 bg-[#2c2420] text-[#faf6f0] relative overflow-hidden">
      <div className="absolute inset-0 opacity-10" style={{ background: 'radial-gradient(circle at 50% 0%, #c9a876 0%, transparent 60%)' }}></div>
      <div className="relative max-w-5xl mx-auto px-6 md:px-10 text-center">
        <Crown className="w-10 h-10 mx-auto mb-5 text-[#c9a876]" />
        {v.kicker && <p className="text-xs tracking-[0.3em] uppercase text-[#c9a876] mb-4">{v.kicker}</p>}
        {v.title && <h2 className="font-serif text-4xl md:text-5xl lg:text-6xl mb-6 leading-tight">{v.title}</h2>}
        {v.subtitle && <p className="text-[#d4c5af] max-w-2xl mx-auto leading-relaxed mb-10 text-lg">{v.subtitle}</p>}
        {perks.length > 0 && (
          <div className="grid sm:grid-cols-3 gap-5 max-w-3xl mx-auto mb-12">
            {perks.map((p, i) => {
              const Icon = ICONS[p.icon] || Gift;
              return (
                <div key={i} className="p-6 border border-[#3d2f24] rounded-2xl">
                  <Icon className="w-6 h-6 text-[#c9a876] mx-auto mb-3" />
                  <p className="text-sm text-[#d4c5af]">{p.label}</p>
                </div>
              );
            })}
          </div>
        )}

        {/* Member-only content */}
        <div className="mt-6 max-w-3xl mx-auto">
          {user ? (
            <div className="relative bg-[#1a1410] border border-[#c9a876]/40 rounded-3xl p-8 md:p-10 text-left">
              <div className="flex items-center gap-2 mb-4 text-[#c9a876]">
                <Sparkles className="w-4 h-4" />
                <span className="text-xs tracking-[0.3em] uppercase">Members Only</span>
              </div>
              <h3 className="font-serif text-2xl md:text-3xl mb-3">Welcome, {(user.fullName || '').split(' ')[0]}.</h3>
              <p className="text-[#d4c5af] leading-relaxed mb-5">You&rsquo;re officially part of Luca&rsquo;s inner circle. Here&rsquo;s what you unlock as a member:</p>
              <ul className="space-y-3 text-[#d4c5af]">
                <li className="flex gap-3"><Star className="w-5 h-5 text-[#c9a876] shrink-0 mt-0.5" /><span><strong className="text-[#faf6f0]">Member code:</strong> <code className="bg-[#c9a876]/15 text-[#c9a876] px-2 py-0.5 rounded">FAMILY10</code> \u2014 10% off your next order.</span></li>
                <li className="flex gap-3"><Gift className="w-5 h-5 text-[#c9a876] shrink-0 mt-0.5" /><span><strong className="text-[#faf6f0]">Early access</strong> to new drops \u2014 48 hours before public release.</span></li>
                <li className="flex gap-3"><Heart className="w-5 h-5 text-[#c9a876] shrink-0 mt-0.5" /><span><strong className="text-[#faf6f0]">Free re-stringing</strong> on any Essential Gemstones bracelet, once a year.</span></li>
                <li className="flex gap-3"><MessageCircle className="w-5 h-5 text-[#c9a876] shrink-0 mt-0.5" /><span>Stories from the studio and behind-the-scenes updates, straight from Luca.</span></li>
              </ul>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => openAuthModal('register')}
              className="group relative w-full text-left bg-[#1a1410] border border-[#3d2f24] hover:border-[#c9a876]/50 rounded-3xl p-8 md:p-10 overflow-hidden transition-colors"
            >
              <div className="pointer-events-none absolute inset-0 backdrop-blur-sm bg-[#1a1410]/30" />
              <div className="relative">
                <div className="flex items-center gap-2 mb-4 text-[#c9a876]">
                  <Lock className="w-4 h-4" />
                  <span className="text-xs tracking-[0.3em] uppercase">Sign up to unlock</span>
                </div>
                <h3 className="font-serif text-2xl md:text-3xl mb-3">Exclusive member perks</h3>
                <p className="text-[#d4c5af] leading-relaxed mb-5">Discount code, early access to new drops, free bracelet re-stringing, and studio stories \u2014 free with your Essential Gemstones account.</p>
                <span className="inline-flex items-center gap-2 px-6 py-3 bg-[#c9a876] text-[#1a1410] rounded-full text-sm tracking-wider uppercase font-medium group-hover:bg-[#d6b885] transition-colors">
                  Join free
                </span>
              </div>
            </button>
          )}
        </div>

        {v.ctaLabel && (
          <div className="mt-10">
            <a href={v.ctaUrl || '#'} target="_blank" rel="noreferrer" className="inline-block px-9 py-4 border border-[#c9a876] text-[#c9a876] rounded-full text-sm tracking-wider uppercase font-medium hover:bg-[#c9a876] hover:text-[#1a1410] transition-colors">{v.ctaLabel}</a>
          </div>
        )}
      </div>
    </section>
  );
}
