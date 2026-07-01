import React, { useEffect, useRef, useState } from 'react';
import { ArrowDown, Volume2, VolumeX } from 'lucide-react';
import { useSite } from '../context/SiteContext';
import { resolveMediaUrl } from '../lib/api';

export default function Hero() {
  const { site } = useSite();
  const h = site.hero || {};
  const mediaUrl = resolveMediaUrl(h.mediaUrl);
  const isVideo = h.mediaType === 'video';
  const videoRef = useRef(null);
  const [muted, setMuted] = useState(true);
  const [showHint, setShowHint] = useState(true);

  // If someone uploads a new video, reset the mute state so autoplay works
  useEffect(() => {
    setMuted(true);
    setShowHint(true);
  }, [mediaUrl, isVideo]);

  const enableSound = async () => {
    const v = videoRef.current;
    if (!v) return;
    v.muted = false;
    v.volume = 1.0;
    setMuted(false);
    setShowHint(false);
    try {
      await v.play();
    } catch (err) {
      // If the browser blocks playback with sound, fall back to muted playback
      v.muted = true;
      setMuted(true);
      setShowHint(true);
    }
  };

  const toggleMute = async (e) => {
    e?.stopPropagation?.();
    const v = videoRef.current;
    if (!v) return;
    if (muted) {
      await enableSound();
    } else {
      v.muted = true;
      setMuted(true);
    }
  };

  return (
    <section id="top" className="relative min-h-screen flex items-center overflow-hidden bg-[#faf6f0]">
      <div className="relative z-10 max-w-7xl mx-auto w-full px-6 md:px-10 pt-32 pb-20 grid lg:grid-cols-2 gap-12 items-center">
        <div className="fade-up">
          {h.kicker && <p className="text-xs tracking-[0.3em] uppercase text-[#8b6b4f] mb-6">{h.kicker}</p>}
          <h1 className="font-serif text-5xl md:text-6xl lg:text-7xl leading-[1.05] text-[#1a1410] mb-6">
            {h.titleLine1}<br />
            <span className="italic font-light">{h.titleLine2}</span>
          </h1>
          {h.subtitle && <p className="text-lg md:text-xl text-[#5a4a3d] max-w-xl mb-10 leading-relaxed">{h.subtitle}</p>}
          <div className="flex flex-wrap items-center gap-4">
            {h.ctaPrimary?.label && (
              <a href={h.ctaPrimary.href || '#shop'} className="px-8 py-4 bg-[#1a1410] text-[#faf6f0] rounded-full text-sm tracking-wider uppercase hover:bg-[#6b4f3a] transition-colors">{h.ctaPrimary.label}</a>
            )}
            {h.ctaSecondary?.label && (
              <a href={h.ctaSecondary.href || '#story'} className="px-8 py-4 border border-[#3d3128] text-[#3d3128] rounded-full text-sm tracking-wider uppercase hover:bg-[#3d3128] hover:text-[#faf6f0] transition-colors">{h.ctaSecondary.label}</a>
            )}
          </div>
        </div>

        <div className="relative h-[420px] md:h-[560px] lg:h-[640px] fade-up" style={{ animationDelay: '0.2s' }}>
          <div className="absolute inset-0 rounded-[280px] overflow-hidden border border-[#d4c5af]/60 bg-[#e8dfd1]">
            {isVideo ? (
              <>
                {/* Clickable overlay to enable sound (kept above the video) */}
                <button
                  type="button"
                  onClick={enableSound}
                  aria-label="Tap for sound"
                  className={`absolute inset-0 z-20 flex flex-col items-center justify-center gap-3 text-[#faf6f0] transition-opacity duration-500 ${muted && showHint ? 'opacity-100 bg-[#1a1410]/25 hover:bg-[#1a1410]/40' : 'opacity-0 pointer-events-none'}`}
                >
                  <span className="w-16 h-16 rounded-full bg-[#faf6f0] text-[#1a1410] flex items-center justify-center shadow-2xl">
                    <Volume2 className="w-7 h-7" />
                  </span>
                  <span className="px-4 py-2 rounded-full bg-[#1a1410]/70 backdrop-blur text-xs tracking-[0.25em] uppercase">
                    Tap for sound
                  </span>
                </button>
                <video
                  ref={videoRef}
                  src={mediaUrl}
                  className="w-full h-full object-cover"
                  autoPlay
                  muted={muted}
                  loop
                  playsInline
                />
                <div className="absolute inset-0 bg-gradient-to-b from-[#1a1410]/20 via-transparent to-[#1a1410]/40 pointer-events-none"></div>
                {/* Small persistent mute toggle (only after sound is enabled) */}
                {!muted && (
                  <button
                    type="button"
                    onClick={toggleMute}
                    aria-label="Mute video"
                    className="absolute bottom-5 right-5 z-30 w-11 h-11 rounded-full bg-[#1a1410]/70 hover:bg-[#1a1410]/90 backdrop-blur text-[#faf6f0] flex items-center justify-center transition-colors"
                  >
                    <Volume2 className="w-5 h-5" />
                  </button>
                )}
                {/* When hint is dismissed but still muted, show a small unmute chip */}
                {muted && !showHint && (
                  <button
                    type="button"
                    onClick={enableSound}
                    aria-label="Unmute video"
                    className="absolute bottom-5 right-5 z-30 w-11 h-11 rounded-full bg-[#1a1410]/70 hover:bg-[#1a1410]/90 backdrop-blur text-[#faf6f0] flex items-center justify-center transition-colors"
                  >
                    <VolumeX className="w-5 h-5" />
                  </button>
                )}
              </>
            ) : (
              <>
                {mediaUrl && <img src={mediaUrl} alt="Hero" className="w-full h-full object-cover" />}
                <div className="absolute inset-0 bg-gradient-to-b from-[#1a1410]/20 via-transparent to-[#1a1410]/40 pointer-events-none"></div>
              </>
            )}
          </div>
          {(h.quoteText || h.quoteAuthor) && (
            <div className="absolute -bottom-6 -left-6 md:-left-12 bg-[#faf6f0] px-6 py-5 shadow-xl rounded-2xl max-w-[240px] float-anim z-30">
              {h.quoteText && <p className="font-serif italic text-[#6b4f3a] text-sm leading-relaxed">&ldquo;{h.quoteText}&rdquo;</p>}
              {h.quoteAuthor && <p className="text-xs text-[#8b6b4f] mt-2 tracking-wider">{h.quoteAuthor}</p>}
            </div>
          )}
        </div>
      </div>

      <a href="#shop" className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 text-[#8b6b4f] hover:text-[#2c2420] transition-colors">
        <span className="text-[10px] tracking-[0.3em] uppercase">Explore</span>
        <ArrowDown className="w-4 h-4 animate-bounce" />
      </a>
    </section>
  );
}
