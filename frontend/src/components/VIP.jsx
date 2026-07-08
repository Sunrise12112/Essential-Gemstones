import React from 'react';
import { Crown, Gift, Star, MessageCircle, Heart, Sparkles, Gem, Lock } from 'lucide-react';
import { useSite } from '../context/SiteContext';
import { useAuth } from '../context/AuthContext';

const ICONS = { Gift, Star, MessageCircle, Heart, Sparkles, Gem, Crown, Lock };

/** Render text with **bold** markdown-lite → <strong>. */
function renderRich(text) {
  if (!text) return null;
  const parts = [];
  const re = /\*\*(.+?)\*\*/g;
  let last = 0;
  let m;
  let i = 0;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) parts.push(<span key={i++}>{text.slice(last, m.index)}</span>);
    parts.push(<strong key={i++} className="text-[#faf6f0]">{m[1]}</strong>);
    last = m.index + m[0].length;
  }
  if (last < text.length) parts.push(<span key={i++}>{text.slice(last)}</span>);
  return parts;
}

export default function VIP() {
  const { site } = useSite();
  const { user, openAuthModal } = useAuth();
  const v = site.vip || {};
  const perks = v.perks || [];
  const memberPerks = v.memberPerks || [];

  const firstName = (user?.fullName || '').split(' ')[0] || 'friend';
  const greeting = (v.memberGreeting || 'Welcome, {name}.').replace(/\{name\}/g, firstName);
  const showMemberBlock = memberPerks.length > 0 || v.memberIntro || v.memberGreeting;
  const showLockedBlock = v.lockedTitle || v.lockedText || v.lockedCtaLabel;

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
        {(user && showMemberBlock) ? (
          <div className="mt-6 max-w-3xl mx-auto">
            <div className="relative bg-[#1a1410] border border-[#c9a876]/40 rounded-3xl p-8 md:p-10 text-left">
              {v.memberKicker && (
                <div className="flex items-center gap-2 mb-4 text-[#c9a876]">
                  <Sparkles className="w-4 h-4" />
                  <span className="text-xs tracking-[0.3em] uppercase">{v.memberKicker}</span>
                </div>
              )}
              {v.memberGreeting && (
                <h3 className="font-serif text-2xl md:text-3xl mb-3">{greeting}</h3>
              )}
              {v.memberIntro && (
                <p className="text-[#d4c5af] leading-relaxed mb-5">{v.memberIntro}</p>
              )}
              {memberPerks.length > 0 && (
                <ul className="space-y-3 text-[#d4c5af]">
                  {memberPerks.map((mp, i) => {
                    const Icon = ICONS[mp.icon] || Star;
                    return (
                      <li key={i} className="flex gap-3">
                        <Icon className="w-5 h-5 text-[#c9a876] shrink-0 mt-0.5" />
                        <span>
                          {mp.title && <strong className="text-[#faf6f0]">{mp.title}:</strong>}{' '}
                          {renderRich(mp.desc)}
                        </span>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          </div>
        ) : (!user && showLockedBlock) ? (
          <div className="mt-6 max-w-3xl mx-auto">
            <button
              type="button"
              onClick={() => openAuthModal('register')}
              className="group relative w-full text-left bg-[#1a1410] border border-[#3d2f24] hover:border-[#c9a876]/50 rounded-3xl p-8 md:p-10 overflow-hidden transition-colors"
            >
              <div className="pointer-events-none absolute inset-0 backdrop-blur-sm bg-[#1a1410]/30" />
              <div className="relative">
                {v.lockedKicker && (
                  <div className="flex items-center gap-2 mb-4 text-[#c9a876]">
                    <Lock className="w-4 h-4" />
                    <span className="text-xs tracking-[0.3em] uppercase">{v.lockedKicker}</span>
                  </div>
                )}
                {v.lockedTitle && <h3 className="font-serif text-2xl md:text-3xl mb-3">{v.lockedTitle}</h3>}
                {v.lockedText && <p className="text-[#d4c5af] leading-relaxed mb-5">{v.lockedText}</p>}
                {v.lockedCtaLabel && (
                  <span className="inline-flex items-center gap-2 px-6 py-3 bg-[#c9a876] text-[#1a1410] rounded-full text-sm tracking-wider uppercase font-medium group-hover:bg-[#d6b885] transition-colors">
                    {v.lockedCtaLabel}
                  </span>
                )}
              </div>
            </button>
          </div>
        ) : null}

        {v.ctaLabel && (
          <div className="mt-10">
            <a href={v.ctaUrl || '#'} target="_blank" rel="noreferrer" className="inline-block px-9 py-4 border border-[#c9a876] text-[#c9a876] rounded-full text-sm tracking-wider uppercase font-medium hover:bg-[#c9a876] hover:text-[#1a1410] transition-colors">{v.ctaLabel}</a>
          </div>
        )}
      </div>
    </section>
  );
}
