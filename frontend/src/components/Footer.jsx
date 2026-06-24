import React, { useState } from 'react';
import { Mail, Heart, Gem, Instagram, Facebook, Loader2 } from 'lucide-react';
import { useToast } from '../hooks/use-toast';
import { useSite } from '../context/SiteContext';
import api from '../lib/api';

export default function Footer() {
  const { site } = useSite();
  const f = site.footer || {};
  const [email, setEmail] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const { toast } = useToast();

  const onSubmit = async (e) => {
    e.preventDefault();
    if (!email) return;
    setSubmitting(true);
    try {
      const { data } = await api.post('/subscribe', { email });
      if (data.alreadySubscribed) {
        toast({ title: 'You\u2019re already with us', description: `${email} is already on the list \u2014 thank you!` });
      } else {
        toast({ title: 'Welcome to the family', description: data.welcomeSent ? 'Check your inbox \u2014 we just sent you a note.' : 'You\u2019re on the list!' });
      }
      setEmail('');
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Something went wrong. Please try again.';
      toast({ title: 'Could not subscribe', description: String(msg), variant: 'destructive' });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <footer id="contact" className="bg-[#1a1410] text-[#d4c5af] pt-20 pb-10">
      <div className="max-w-7xl mx-auto px-6 md:px-10">
        <div className="grid lg:grid-cols-2 gap-12 pb-14 border-b border-[#3d2f24]">
          <div>
            <div className="flex items-center gap-2 mb-5">
              <Gem className="w-5 h-5 text-[#c9a876]" />
              <span className="font-serif text-2xl text-[#faf6f0]">{f.brand || 'Essential Gemstones'}</span>
            </div>
            {f.tagline && <p className="text-[#bfae95] leading-relaxed max-w-md mb-6">{f.tagline}</p>}
            <div className="flex items-center gap-3">
              {f.socials?.instagram && <a href={f.socials.instagram} aria-label="Instagram" className="w-10 h-10 rounded-full border border-[#3d2f24] flex items-center justify-center hover:border-[#c9a876] hover:text-[#c9a876] transition-colors"><Instagram className="w-4 h-4" /></a>}
              {f.socials?.facebook && <a href={f.socials.facebook} aria-label="Facebook" className="w-10 h-10 rounded-full border border-[#3d2f24] flex items-center justify-center hover:border-[#c9a876] hover:text-[#c9a876] transition-colors"><Facebook className="w-4 h-4" /></a>}
              {f.email && <a href={`mailto:${f.email}`} aria-label="Email" className="w-10 h-10 rounded-full border border-[#3d2f24] flex items-center justify-center hover:border-[#c9a876] hover:text-[#c9a876] transition-colors"><Mail className="w-4 h-4" /></a>}
            </div>
          </div>
          <div>
            {f.newsletterKicker && <p className="text-xs tracking-[0.3em] uppercase text-[#c9a876] mb-4">{f.newsletterKicker}</p>}
            {f.newsletterTitle && <h3 className="font-serif text-2xl md:text-3xl text-[#faf6f0] mb-5 leading-tight">{f.newsletterTitle}</h3>}
            <form onSubmit={onSubmit} className="flex flex-col sm:flex-row gap-3 mb-6">
              <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="your@email.com" disabled={submitting} className="flex-1 px-5 py-3.5 bg-transparent border border-[#3d2f24] focus:border-[#c9a876] rounded-full text-[#faf6f0] placeholder:text-[#7a6a55] outline-none transition-colors disabled:opacity-60" />
              <button type="submit" disabled={submitting} className="px-7 py-3.5 bg-[#c9a876] text-[#1a1410] rounded-full text-sm tracking-wider uppercase font-medium hover:bg-[#d6b885] transition-colors disabled:opacity-60 inline-flex items-center justify-center gap-2">
                {submitting && <Loader2 className="w-4 h-4 animate-spin" />}
                {submitting ? 'Sending\u2026' : 'Subscribe'}
              </button>
            </form>
            {f.email && <p className="text-sm text-[#bfae95]">Email us at <a href={`mailto:${f.email}`} className="text-[#c9a876] hover:underline">{f.email}</a></p>}
            {(f.donateTitle || f.donateUrl) && (
              <div className="mt-8 p-5 border border-[#3d2f24] rounded-2xl">
                {f.donateTitle && <p className="text-xs tracking-[0.2em] uppercase text-[#c9a876] mb-2">{f.donateTitle}</p>}
                {f.donateText && <p className="text-sm text-[#bfae95] mb-4 leading-relaxed">{f.donateText}</p>}
                {f.donateUrl && <a href={f.donateUrl} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 text-sm text-[#faf6f0] hover:text-[#c9a876] transition-colors"><Heart className="w-4 h-4" /> {f.donateLabel || 'Donate Now'}</a>}
              </div>
            )}
          </div>
        </div>
        <div className="pt-8 flex flex-col md:flex-row gap-4 items-center justify-between text-xs tracking-wider text-[#7a6a55]">
          <p>© {new Date().getFullYear()} {f.brand || 'Essential Gemstones'}. {f.copyright || ''}</p>
          {f.quote && <p className="font-serif italic text-[#bfae95]">{f.quote}</p>}
        </div>
      </div>
    </footer>
  );
}
