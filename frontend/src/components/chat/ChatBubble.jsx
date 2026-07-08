import React, { useEffect, useRef, useState } from 'react';
import { MessageCircle, X, Send, Sparkles, Gem, Loader2 } from 'lucide-react';
import { API } from '../../lib/api';

const MODES = [
  { key: 'ask-luca', label: 'Ask Luca', icon: MessageCircle, hello: 'Hi! I\u2019m here to help with questions about our bracelets, care, chakras, or shipping. What can I answer for you?' },
  { key: 'stone-guide', label: 'Find my stone', icon: Sparkles, hello: 'I can help you find the stone that matches your intention. What are you looking to bring into your life right now — grounding, protection, love, clarity, courage?' },
];

const SESSION_STORAGE_KEY = 'eg_chat_sessions';

function loadSessions() {
  try { return JSON.parse(localStorage.getItem(SESSION_STORAGE_KEY)) || {}; } catch (e) { return {}; }
}
function saveSessions(map) {
  try { localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(map)); } catch (e) { /* ignore */ }
}

export default function ChatBubble() {
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState('ask-luca');
  const [sessionsByMode, setSessionsByMode] = useState(loadSessions());
  const [messagesByMode, setMessagesByMode] = useState({ 'ask-luca': [], 'stone-guide': [] });
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState('');
  const bodyRef = useRef(null);
  const abortRef = useRef(null);

  const currentMessages = messagesByMode[mode] || [];

  useEffect(() => {
    // seed hello message if empty
    setMessagesByMode((s) => {
      if ((s[mode] || []).length > 0) return s;
      const hello = MODES.find((m) => m.key === mode)?.hello;
      return { ...s, [mode]: hello ? [{ role: 'assistant', content: hello }] : [] };
    });
  }, [mode]);

  useEffect(() => {
    if (bodyRef.current) bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
  }, [currentMessages, streaming]);

  const send = async () => {
    const text = input.trim();
    if (!text || streaming) return;
    setInput('');
    setError('');
    setStreaming(true);

    // Optimistically add user msg + placeholder assistant
    setMessagesByMode((s) => ({
      ...s,
      [mode]: [...(s[mode] || []), { role: 'user', content: text }, { role: 'assistant', content: '' }],
    }));

    try {
      const controller = new AbortController();
      abortRef.current = controller;
      const res = await fetch(`${API}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode, message: text, sessionId: sessionsByMode[mode] || null }),
        signal: controller.signal,
      });
      if (!res.ok || !res.body) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Chat error ${res.status}`);
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      // eslint-disable-next-line no-constant-condition
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split('\n\n');
        buffer = events.pop() || '';
        for (const raw of events) {
          if (!raw) continue;
          let eventName = 'message';
          let dataLines = [];
          for (const line of raw.split('\n')) {
            if (line.startsWith('event:')) eventName = line.slice(6).trim();
            else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim());
          }
          const data = dataLines.join('\n').replace(/\\n/g, '\n');
          if (eventName === 'session') {
            const newMap = { ...sessionsByMode, [mode]: data };
            setSessionsByMode(newMap);
            saveSessions(newMap);
          } else if (eventName === 'error') {
            setError(data || 'Something went wrong.');
          } else if (eventName === 'done') {
            // finished
          } else {
            // token chunk
            setMessagesByMode((s) => {
              const list = [...(s[mode] || [])];
              const last = list[list.length - 1];
              if (last && last.role === 'assistant') {
                list[list.length - 1] = { ...last, content: (last.content || '') + data };
              }
              return { ...s, [mode]: list };
            });
          }
        }
      }
    } catch (e) {
      if (e.name !== 'AbortError') {
        setError(e.message || 'Chat unavailable.');
      }
    } finally {
      setStreaming(false);
      abortRef.current = null;
    }
  };

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  const currentModeInfo = MODES.find((m) => m.key === mode);

  return (
    <>
      {/* Floating button */}
      <button
        onClick={() => setOpen(!open)}
        aria-label={open ? 'Close chat' : 'Open chat'}
        className={`fixed bottom-6 right-6 z-[60] w-14 h-14 rounded-full shadow-2xl flex items-center justify-center transition-all duration-300 ${open ? 'bg-[#faf6f0] text-[#1a1410]' : 'bg-[#1a1410] text-[#c9a876] hover:scale-105'}`}
      >
        {open ? <X className="w-6 h-6" /> : <MessageCircle className="w-6 h-6" />}
      </button>

      {/* Chat panel */}
      {open && (
        <div className="fixed bottom-24 right-6 z-[59] w-[calc(100vw-3rem)] sm:w-96 max-h-[75vh] bg-[#faf6f0] rounded-3xl shadow-2xl border border-[#e8dfd1] flex flex-col overflow-hidden animate-in slide-in-from-bottom-4">
          {/* Header */}
          <div className="bg-[#1a1410] text-[#faf6f0] px-5 py-4 flex-shrink-0">
            <div className="flex items-center gap-2 mb-2">
              <Gem className="w-4 h-4 text-[#c9a876]" />
              <span className="text-xs tracking-[0.25em] uppercase text-[#c9a876]">Essential Gemstones</span>
            </div>
            <div className="flex items-center gap-2">
              {MODES.map((m) => (
                <button
                  key={m.key}
                  onClick={() => setMode(m.key)}
                  className={`text-xs px-3 py-1.5 rounded-full transition-colors inline-flex items-center gap-1.5 ${mode === m.key ? 'bg-[#c9a876] text-[#1a1410]' : 'border border-[#3d2f24] text-[#d4c5af] hover:border-[#c9a876]/50'}`}
                >
                  <m.icon className="w-3 h-3" /> {m.label}
                </button>
              ))}
            </div>
          </div>

          {/* Body */}
          <div ref={bodyRef} className="flex-1 overflow-y-auto p-4 space-y-3 bg-[#faf6f0]">
            {currentMessages.map((m, i) => (
              <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[85%] px-4 py-2.5 rounded-2xl whitespace-pre-wrap text-sm leading-relaxed ${m.role === 'user' ? 'bg-[#1a1410] text-[#faf6f0] rounded-br-sm' : 'bg-white text-[#2c2420] rounded-bl-sm border border-[#e8dfd1]'}`}>
                  {m.content || (m.role === 'assistant' && streaming ? <Loader2 className="w-4 h-4 animate-spin text-[#8b6b4f]" /> : '')}
                </div>
              </div>
            ))}
            {error && (
              <div className="text-xs text-red-600 bg-red-50 border border-red-200 rounded-xl px-3 py-2">{error}</div>
            )}
          </div>

          {/* Input */}
          <div className="border-t border-[#e8dfd1] p-3 flex gap-2 items-end bg-white">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder={currentModeInfo?.key === 'stone-guide' ? 'Share what you\u2019re looking for\u2026' : 'Ask us anything\u2026'}
              rows={1}
              className="flex-1 resize-none max-h-32 px-4 py-2.5 border border-[#e8dfd1] rounded-2xl focus:border-[#6b4f3a] focus:outline-none text-sm bg-[#faf6f0]"
            />
            <button
              onClick={send}
              disabled={streaming || !input.trim()}
              aria-label="Send"
              className="w-10 h-10 rounded-full bg-[#1a1410] text-[#faf6f0] flex items-center justify-center hover:bg-[#6b4f3a] disabled:opacity-40 disabled:hover:bg-[#1a1410] transition-colors shrink-0"
            >
              {streaming ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            </button>
          </div>
          <p className="text-[10px] text-[#8b6b4f] text-center py-2 bg-[#faf6f0]">Powered by AI · not human · double-check important info</p>
        </div>
      )}
    </>
  );
}
