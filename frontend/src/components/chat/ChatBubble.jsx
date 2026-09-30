import React, { useEffect, useRef, useState, useCallback } from 'react';
import { MessageCircle, X, Send, Sparkles, Gem, Loader2, Plus, History, Trash2, Pencil, Check, Lock } from 'lucide-react';
import { API } from '../../lib/api';
import { getClientId, chatAuthHeaders } from '../../lib/chatIdentity';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../hooks/use-toast';

const MODES = [
  { key: 'ask-luca', label: 'Ask Luca', hello: 'Hi! I\u2019m here to help with questions about our bracelets, care, chakras, or shipping. What can I answer for you?' },
  { key: 'stone-guide', label: 'Find my stone', hello: 'I can help you find the stone that matches your intention. What are you looking to bring into your life right now \u2014 grounding, protection, love, clarity, courage?' },
];

export default function ChatBubble() {
  const { user, openAuthModal } = useAuth();
  const [open, setOpen] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [mode, setMode] = useState('ask-luca');
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState('');
  const [editingTitle, setEditingTitle] = useState(false);
  const [titleDraft, setTitleDraft] = useState('');
  const bodyRef = useRef(null);
  const { toast } = useToast();

  // Ensure client id exists
  useEffect(() => { getClientId(); }, []);

  const currentSession = sessions.find((s) => s.id === currentSessionId);

  const loadSessions = useCallback(async () => {
    if (!user) { setSessions([]); return; }
    try {
      const res = await fetch(`${API}/chat/sessions?mode=${mode}`, { headers: chatAuthHeaders() });
      if (res.ok) setSessions(await res.json());
    } catch (e) { /* ignore */ }
  }, [mode, user]);

  useEffect(() => {
    if (open && user) loadSessions();
    // Also refresh when principal changes (login/logout)
  }, [open, user, loadSessions]);

  useEffect(() => {
    // When mode changes, start fresh
    setCurrentSessionId(null);
    const hello = MODES.find((m) => m.key === mode)?.hello;
    setMessages(hello ? [{ role: 'assistant', content: hello }] : []);
    loadSessions();
  }, [mode, loadSessions]);

  useEffect(() => {
    if (bodyRef.current) bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
  }, [messages, streaming]);

  const loadSession = async (id) => {
    setShowHistory(false);
    setError('');
    try {
      const res = await fetch(`${API}/chat/session/${id}`, { headers: chatAuthHeaders() });
      if (!res.ok) throw new Error('Chat not found');
      const data = await res.json();
      setCurrentSessionId(data.id);
      setMode(data.mode || mode);
      setMessages((data.messages || []).map((m) => ({ role: m.role, content: m.content })));
    } catch (e) {
      toast({ title: 'Could not open chat', description: e.message, variant: 'destructive' });
    }
  };

  const newChat = () => {
    setCurrentSessionId(null);
    const hello = MODES.find((m) => m.key === mode)?.hello;
    setMessages(hello ? [{ role: 'assistant', content: hello }] : []);
    setShowHistory(false);
    setError('');
  };

  const send = async () => {
    const text = input.trim();
    if (!text || streaming) return;
    setInput('');
    setError('');
    setStreaming(true);
    setMessages((s) => [...s, { role: 'user', content: text }, { role: 'assistant', content: '' }]);

    try {
      const res = await fetch(`${API}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...chatAuthHeaders() },
        body: JSON.stringify({ mode, message: text, sessionId: currentSessionId }),
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
          const dataLines = [];
          for (const line of raw.split('\n')) {
            if (line.startsWith('event:')) eventName = line.slice(6).trim();
            else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim());
          }
          const data = dataLines.join('\n').replace(/\\n/g, '\n');
          if (eventName === 'session') setCurrentSessionId(data);
          else if (eventName === 'error') setError(data || 'Something went wrong.');
          else if (eventName !== 'done') {
            setMessages((s) => {
              const list = [...s];
              const last = list[list.length - 1];
              if (last && last.role === 'assistant') list[list.length - 1] = { ...last, content: (last.content || '') + data };
              return list;
            });
          }
        }
      }
      loadSessions();
    } catch (e) {
      setError(e.message || 'Chat unavailable.');
    } finally {
      setStreaming(false);
    }
  };

  const deleteSession = async (id, e) => {
    e?.stopPropagation?.();
    if (!window.confirm('Delete this chat forever?')) return;
    try {
      await fetch(`${API}/chat/session/${id}`, { method: 'DELETE', headers: chatAuthHeaders() });
      if (currentSessionId === id) newChat();
      loadSessions();
    } catch (err) { /* ignore */ }
  };

  const startRename = () => {
    if (!currentSession) return;
    setTitleDraft(currentSession.title || '');
    setEditingTitle(true);
  };

  const saveRename = async () => {
    if (!currentSessionId) { setEditingTitle(false); return; }
    const t = titleDraft.trim();
    if (!t) { setEditingTitle(false); return; }
    try {
      await fetch(`${API}/chat/session/${currentSessionId}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json', ...chatAuthHeaders() },
        body: JSON.stringify({ title: t }),
      });
      loadSessions();
      setEditingTitle(false);
    } catch (err) { /* ignore */ }
  };

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <>
      <button onClick={() => setOpen(!open)} aria-label={open ? 'Close chat' : 'Open chat'}
        data-testid="chat-bubble-toggle"
        className={`fixed bottom-6 right-6 z-[60] w-14 h-14 rounded-full shadow-2xl flex items-center justify-center transition-all duration-300 ${open ? 'bg-[#faf6f0] text-[#1a1410]' : 'bg-[#1a1410] text-[#c9a876] hover:scale-105'}`}>
        {open ? <X className="w-6 h-6" /> : <MessageCircle className="w-6 h-6" />}
      </button>

      {open && !user && (
        <div className="fixed bottom-24 right-6 z-[59] w-[calc(100vw-3rem)] sm:w-[420px] bg-[#faf6f0] rounded-3xl shadow-2xl border border-[#e8dfd1] overflow-hidden animate-in slide-in-from-bottom-4" data-testid="chat-login-gate">
          <div className="bg-[#1a1410] text-[#faf6f0] px-5 py-4 flex items-center gap-2">
            <Gem className="w-4 h-4 text-[#c9a876]" />
            <span className="text-xs tracking-[0.2em] uppercase text-[#c9a876]">Members only</span>
          </div>
          <div className="p-6 text-center">
            <div className="w-14 h-14 rounded-full bg-[#f1e7d6] flex items-center justify-center mx-auto mb-4">
              <Lock className="w-6 h-6 text-[#6b4f3a]" />
            </div>
            <h3 className="text-xl text-[#1a1410] mb-2" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
              Sign in to chat with Luca
            </h3>
            <p className="text-sm text-[#6b4f3a] leading-relaxed mb-5">
              Your AI conversations are saved to your account so Luca remembers you every time. Create a free member account or sign in to continue.
            </p>
            <div className="flex flex-col gap-2">
              <button
                data-testid="chat-gate-signup-btn"
                onClick={() => { setOpen(false); openAuthModal('register'); }}
                className="w-full py-2.5 rounded-full bg-[#1a1410] text-[#faf6f0] text-sm tracking-wider uppercase hover:bg-[#6b4f3a] transition-colors">
                Create free account
              </button>
              <button
                data-testid="chat-gate-login-btn"
                onClick={() => { setOpen(false); openAuthModal('login'); }}
                className="w-full py-2.5 rounded-full border border-[#1a1410] text-[#1a1410] text-sm tracking-wider uppercase hover:bg-[#1a1410] hover:text-[#faf6f0] transition-colors">
                Sign in
              </button>
            </div>
          </div>
        </div>
      )}

      {open && user && (
        <div className="fixed bottom-24 right-6 z-[59] w-[calc(100vw-3rem)] sm:w-[440px] h-[75vh] max-h-[720px] bg-[#faf6f0] rounded-3xl shadow-2xl border border-[#e8dfd1] flex flex-col overflow-hidden animate-in slide-in-from-bottom-4">
          {/* Header */}
          <div className="bg-[#1a1410] text-[#faf6f0] px-4 py-3 flex-shrink-0">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2 min-w-0">
                <Gem className="w-4 h-4 text-[#c9a876] shrink-0" />
                {editingTitle && currentSessionId ? (
                  <div className="flex items-center gap-1 flex-1">
                    <input value={titleDraft} onChange={(e) => setTitleDraft(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') saveRename(); if (e.key === 'Escape') setEditingTitle(false); }} autoFocus className="flex-1 px-2 py-1 bg-[#241b15] text-[#faf6f0] rounded text-xs outline-none border border-[#3d2f24]" />
                    <button onClick={saveRename} className="text-[#c9a876] hover:text-[#faf6f0]" aria-label="Save"><Check className="w-3.5 h-3.5" /></button>
                  </div>
                ) : (
                  <>
                    <span className="text-xs tracking-[0.2em] uppercase text-[#c9a876] truncate">{currentSession?.title || 'New chat'}</span>
                    {currentSessionId && <button onClick={startRename} className="text-[#8b6b4f] hover:text-[#c9a876] shrink-0" aria-label="Rename"><Pencil className="w-3 h-3" /></button>}
                  </>
                )}
              </div>
              <div className="flex items-center gap-1 shrink-0">
                <button onClick={() => setShowHistory(!showHistory)} title="History" aria-label="History" className={`w-8 h-8 rounded-full flex items-center justify-center transition-colors ${showHistory ? 'bg-[#c9a876] text-[#1a1410]' : 'hover:bg-[#241b15]'}`}><History className="w-4 h-4" /></button>
                <button onClick={newChat} title="New chat" aria-label="New chat" className="w-8 h-8 rounded-full hover:bg-[#241b15] flex items-center justify-center"><Plus className="w-4 h-4" /></button>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {MODES.map((m) => (
                <button key={m.key} onClick={() => setMode(m.key)}
                  className={`text-xs px-3 py-1.5 rounded-full transition-colors ${mode === m.key ? 'bg-[#c9a876] text-[#1a1410]' : 'border border-[#3d2f24] text-[#d4c5af] hover:border-[#c9a876]/50'}`}>
                  {m.label}
                </button>
              ))}
            </div>
          </div>

          {/* Body / History */}
          <div className="flex-1 min-h-0 relative">
            {showHistory ? (
              <div className="absolute inset-0 bg-[#faf6f0] overflow-y-auto">
                <div className="p-3 border-b border-[#e8dfd1] flex items-center justify-between">
                  <p className="text-xs tracking-[0.2em] uppercase text-[#8b6b4f]">Your chats</p>
                  <button onClick={newChat} className="text-xs px-3 py-1 rounded-full bg-[#1a1410] text-[#faf6f0] inline-flex items-center gap-1"><Plus className="w-3 h-3" /> New</button>
                </div>
                {sessions.length === 0 ? (
                  <p className="text-center text-sm text-[#8b6b4f] italic p-8">No chats yet in this mode. Start one to save it here.</p>
                ) : (
                  <div className="divide-y divide-[#e8dfd1]">
                    {sessions.map((s) => (
                      <button key={s.id} onClick={() => loadSession(s.id)} className={`w-full text-left px-4 py-3 flex items-start justify-between gap-3 group hover:bg-white ${s.id === currentSessionId ? 'bg-white' : ''}`}>
                        <div className="min-w-0 flex-1">
                          <p className="text-sm text-[#1a1410] truncate font-medium">{s.title || 'New chat'}</p>
                          <p className="text-xs text-[#8b6b4f] truncate">{s.lastMessagePreview}</p>
                          <p className="text-[10px] text-[#8b6b4f] mt-0.5">{s.updatedAt ? new Date(s.updatedAt).toLocaleString() : ''}</p>
                        </div>
                        <button onClick={(e) => deleteSession(s.id, e)} className="text-[#8b6b4f] hover:text-red-700 opacity-0 group-hover:opacity-100 transition-opacity" aria-label="Delete"><Trash2 className="w-4 h-4" /></button>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div ref={bodyRef} className="absolute inset-0 overflow-y-auto p-4 space-y-3">
                {messages.map((m, i) => (
                  <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[85%] px-4 py-2.5 rounded-2xl whitespace-pre-wrap text-sm leading-relaxed ${m.role === 'user' ? 'bg-[#1a1410] text-[#faf6f0] rounded-br-sm' : 'bg-white text-[#2c2420] rounded-bl-sm border border-[#e8dfd1]'}`}>
                      {m.content || (m.role === 'assistant' && streaming ? <Loader2 className="w-4 h-4 animate-spin text-[#8b6b4f]" /> : '')}
                    </div>
                  </div>
                ))}
                {error && <div className="text-xs text-red-600 bg-red-50 border border-red-200 rounded-xl px-3 py-2">{error}</div>}
              </div>
            )}
          </div>

          {/* Input */}
          {!showHistory && (
            <div className="border-t border-[#e8dfd1] p-3 flex gap-2 items-end bg-white shrink-0">
              <textarea value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={onKeyDown}
                placeholder={mode === 'stone-guide' ? 'Share what you\u2019re looking for\u2026' : 'Ask us anything\u2026'}
                rows={1} className="flex-1 resize-none max-h-32 px-4 py-2.5 border border-[#e8dfd1] rounded-2xl focus:border-[#6b4f3a] focus:outline-none text-sm bg-[#faf6f0]" />
              <button onClick={send} disabled={streaming || !input.trim()} aria-label="Send"
                className="w-10 h-10 rounded-full bg-[#1a1410] text-[#faf6f0] flex items-center justify-center hover:bg-[#6b4f3a] disabled:opacity-40 disabled:hover:bg-[#1a1410] transition-colors shrink-0">
                {streaming ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              </button>
            </div>
          )}
          <p className="text-[10px] text-[#8b6b4f] text-center py-1.5 bg-[#faf6f0]">
            {user ? `Signed in \u2014 your chats are saved to your account` : 'Chats saved to this browser'}
            {' \u00b7 '}
            <a href="https://nano-ai.org" target="_blank" rel="noreferrer" data-testid="chat-built-by-nano" className="underline hover:text-[#6b4f3a] transition-colors">Built by Nano AI</a>
          </p>
        </div>
      )}
    </>
  );
}
