import React, { useState } from 'react';
import { Mail, Heart, Gem, Instagram, Facebook } from 'lucide-react';
import { useToast } from '../hooks/use-toast';

export default function Footer() {
  const [email, setEmail] = useState('');
  const { toast } = useToast();

  const onSubmit = (e) => {
    e.preventDefault();
    if (!email) return;
    toast({ title: 'Welcome to the family', description: `We\u2019ll keep ${email} in the loop on new collections and stories.` });
    setEmail('');
  };

  return (
    <footer id="contact" className="bg-[#1a1410] text-[#d4c5af] pt-20 pb-10">
      <div className="max-w-7xl mx-auto px-6 md:px-10">
        <div className="grid lg:grid-cols-2 gap-12 pb-14 border-b border-[#3d2f24]">
          <div>
            <div className="flex items-center gap-2 mb-5">
              <Gem className="w-5 h-5 text-[#c9a876]" />
              <span className="font-serif text-2xl text-[#faf6f0]">Essential Gemstones</span>
            </div>
            <p className="text-[#bfae95] leading-relaxed max-w-md mb-6">
              Join our growing community of crystal lovers, nature seekers, and everyday wearers. Be the first to know about new collections, restocks, and stories from the studio.
            </p>
            <div className="flex items-center gap-3">
              <a href="#" aria-label="Instagram" className="w-10 h-10 rounded-full border border-[#3d2f24] flex items-center justify-center hover:border-[#c9a876] hover:text-[#c9a876] transition-colors"><Instagram className="w-4 h-4" /></a>
              <a href="#" aria-label="Facebook" className="w-10 h-10 rounded-full border border-[#3d2f24] flex items-center justify-center hover:border-[#c9a876] hover:text-[#c9a876] transition-colors"><Facebook className="w-4 h-4" /></a>
              <a href="mailto:Essentialgemstones@googlegroups.com" aria-label="Email" className="w-10 h-10 rounded-full border border-[#3d2f24] flex items-center justify-center hover:border-[#c9a876] hover:text-[#c9a876] transition-colors"><Mail className="w-4 h-4" /></a>
            </div>
          </div>

          <div>
            <p className="text-xs tracking-[0.3em] uppercase text-[#c9a876] mb-4">Stay Connected</p>
            <h3 className="font-serif text-2xl md:text-3xl text-[#faf6f0] mb-5 leading-tight">Get the latest from the studio.</h3>
            <form onSubmit={onSubmit} className="flex flex-col sm:flex-row gap-3 mb-6">
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="your@email.com"
                className="flex-1 px-5 py-3.5 bg-transparent border border-[#3d2f24] focus:border-[#c9a876] rounded-full text-[#faf6f0] placeholder:text-[#7a6a55] outline-none transition-colors"
              />
              <button type="submit" className="px-7 py-3.5 bg-[#c9a876] text-[#1a1410] rounded-full text-sm tracking-wider uppercase font-medium hover:bg-[#d6b885] transition-colors">Subscribe</button>
            </form>
            <p className="text-sm text-[#bfae95]">Email us at <a href="mailto:Essentialgemstones@googlegroups.com" className="text-[#c9a876] hover:underline">Essentialgemstones@googlegroups.com</a></p>

            <div className="mt-8 p-5 border border-[#3d2f24] rounded-2xl">
              <p className="text-xs tracking-[0.2em] uppercase text-[#c9a876] mb-2">Support Luca&rsquo;s Dream</p>
              <p className="text-sm text-[#bfae95] mb-4 leading-relaxed">Every donation — big or small — helps keep Essential Gemstones growing.</p>
              <a href="https://donate.stripe.com/00w14g5vZfVo88f2mrgYU01" target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 text-sm text-[#faf6f0] hover:text-[#c9a876] transition-colors">
                <Heart className="w-4 h-4" /> Donate Now
              </a>
            </div>
          </div>
        </div>

        <div className="pt-8 flex flex-col md:flex-row gap-4 items-center justify-between text-xs tracking-wider text-[#7a6a55]">
          <p>© {new Date().getFullYear()} Essential Gemstones. Handmade with intention.</p>
          <p className="font-serif italic text-[#bfae95]">“Thank you from the bottom of my heart.” — Luca</p>
        </div>
      </div>
    </footer>
  );
}
