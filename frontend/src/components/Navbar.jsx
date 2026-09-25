import React, { useState, useEffect } from 'react';
import { Menu, X, Gem, User, LogOut, Sparkles, ChevronDown } from 'lucide-react';
import { useSite } from '../context/SiteContext';
import { useAuth } from '../context/AuthContext';

export default function Navbar() {
  const { site } = useSite();
  const { user, logout, openAuthModal } = useAuth();
  const nav = site.navbar || {};
  const links = nav.links || [];
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);
  const [userMenu, setUserMenu] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    window.addEventListener('scroll', onScroll);
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  useEffect(() => {
    const onClick = (e) => {
      if (!e.target.closest('[data-user-menu]')) setUserMenu(false);
    };
    if (userMenu) document.addEventListener('click', onClick);
    return () => document.removeEventListener('click', onClick);
  }, [userMenu]);

  const firstName = (user?.fullName || '').split(' ')[0] || 'Member';

  return (
    <header className={`fixed top-0 left-0 right-0 z-50 transition-colors duration-500 ${scrolled ? 'bg-[#faf6f0]/95 backdrop-blur-md border-b border-[#e8dfd1]' : 'bg-transparent'}`}>
      <div className="max-w-7xl mx-auto px-6 md:px-10 py-5 flex items-center justify-between">
        <a href="#top" data-testid="navbar-brand-link" className="min-w-0 flex items-center gap-2 group">
          <Gem className="w-5 h-5 text-[#6b4f3a]" />
          <span className="font-serif text-xl tracking-wide text-[#2c2420]">{nav.brand || 'Essential Gemstones'}</span>
        </a>

        <nav className="hidden xl:flex items-center gap-8">
          {links.map((l, i) => (
            <a key={i} href={l.href} data-testid={`navbar-desktop-link-${i}`} className="text-sm tracking-wide text-[#3d3128] hover:text-[#6b4f3a] transition-colors relative group">
              {l.label}
              <span className="absolute -bottom-1 left-0 h-px w-0 bg-[#6b4f3a] transition-all duration-300 group-hover:w-full"></span>
            </a>
          ))}

          {user ? (
            <div className="relative" data-user-menu>
              <button data-testid="navbar-account-menu-toggle" onClick={(e) => { e.stopPropagation(); setUserMenu(!userMenu); }} className="inline-flex items-center gap-2 px-3.5 py-2 rounded-full bg-[#faf6f0] border border-[#e8dfd1] hover:border-[#c9a876] transition-colors">
                <span className="w-7 h-7 rounded-full bg-[#1a1410] text-[#c9a876] flex items-center justify-center text-xs font-medium">{firstName.charAt(0).toUpperCase()}</span>
                <span className="text-sm text-[#2c2420]">{firstName}</span>
                <span className="text-[9px] tracking-[0.2em] uppercase bg-[#c9a876]/20 text-[#6b4f3a] px-1.5 py-0.5 rounded">Member</span>
                <ChevronDown className="w-3.5 h-3.5 text-[#8b6b4f]" />
              </button>
              {userMenu && (
                <div data-testid="navbar-account-menu" className="absolute right-0 mt-2 w-56 bg-white border border-[#e8dfd1] rounded-2xl shadow-xl overflow-hidden">
                  <div className="px-4 py-3 border-b border-[#e8dfd1]">
                    <p data-testid="navbar-account-name" className="text-sm font-medium text-[#1a1410]">{user.fullName}</p>
                    <p data-testid="navbar-account-email" className="text-xs text-[#8b6b4f] truncate">{user.email}</p>
                  </div>
                  <a href="#members" data-testid="navbar-member-area-link" className="flex items-center gap-2 px-4 py-3 text-sm text-[#3d3128] hover:bg-[#faf6f0]"><Sparkles className="w-4 h-4 text-[#c9a876]" /> Member area</a>
                  <button data-testid="navbar-sign-out" onClick={() => { logout(); setUserMenu(false); }} className="w-full flex items-center gap-2 px-4 py-3 text-sm text-[#3d3128] hover:bg-[#faf6f0]"><LogOut className="w-4 h-4" /> Sign out</button>
                </div>
              )}
            </div>
          ) : (
            <>
              <button data-testid="navbar-sign-in" onClick={() => openAuthModal('login')} className="text-sm tracking-wide text-[#3d3128] hover:text-[#6b4f3a] transition-colors inline-flex items-center gap-1">
                <User className="w-4 h-4" /> Sign in
              </button>
              {nav.ctaLabel && (
                <a data-testid="navbar-cta" href={nav.ctaHref || '#shop'} className="px-5 py-2.5 text-sm bg-[#2c2420] text-[#faf6f0] rounded-full hover:bg-[#6b4f3a] transition-colors">{nav.ctaLabel}</a>
              )}
            </>
          )}
        </nav>

        <button data-testid="navbar-mobile-menu-toggle" className="xl:hidden shrink-0 text-[#2c2420]" onClick={() => setOpen(!open)} aria-label="menu" aria-expanded={open} aria-controls="mobile-navigation">
          {open ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
        </button>
      </div>

      {open && (
        <div id="mobile-navigation" data-testid="navbar-mobile-menu" className="xl:hidden max-h-[75dvh] overflow-y-auto bg-[#faf6f0] border-t border-[#e8dfd1] px-6 py-6 flex flex-col gap-4">
          {links.map((l, i) => (
            <a key={i} href={l.href} data-testid={`navbar-mobile-link-${i}`} onClick={() => setOpen(false)} className="text-base text-[#3d3128] hover:text-[#6b4f3a]">{l.label}</a>
          ))}
          {user ? (
            <>
              <div className="flex items-center gap-2 pt-2">
                <span className="w-8 h-8 rounded-full bg-[#1a1410] text-[#c9a876] flex items-center justify-center text-xs">{firstName.charAt(0).toUpperCase()}</span>
                <div>
                  <p data-testid="navbar-mobile-account-name" className="text-sm text-[#1a1410]">{user.fullName}</p>
                  <p className="text-xs text-[#8b6b4f]">Member</p>
                </div>
              </div>
              <button data-testid="navbar-mobile-sign-out" onClick={() => { logout(); setOpen(false); }} className="text-sm text-[#3d3128] inline-flex items-center gap-2"><LogOut className="w-4 h-4" /> Sign out</button>
            </>
          ) : (
            <>
              <button data-testid="navbar-mobile-sign-in" onClick={() => { openAuthModal('login'); setOpen(false); }} className="text-left text-base text-[#3d3128]">Sign in</button>
              <button data-testid="navbar-mobile-join" onClick={() => { openAuthModal('register'); setOpen(false); }} className="mt-1 inline-block w-fit px-5 py-2.5 text-sm bg-[#2c2420] text-[#faf6f0] rounded-full">Join</button>
            </>
          )}
        </div>
      )}
    </header>
  );
}
