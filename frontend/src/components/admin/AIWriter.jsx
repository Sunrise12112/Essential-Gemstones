import React, { useEffect, useRef, useState } from 'react';
import { Sparkles, X, Send, Loader2, ClipboardCheck } from 'lucide-react';
import { API } from '../../lib/api';
import { useToast } from '../../hooks/use-toast';

export default function AIWriter({ open, onClose, onInsert, hint = '' }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [copied, setCopied] = useState(-1);
  const bodyRef = useRef(null);
  const { toast } = useToast();

  useEffect(() => {
    if (open) {
      setMessages([]);
      setSessionId(null);
      setInput(hint || '');
    }
  }, [open, hint]);

  useEffect(() => {
    if (bodyRef.current) bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
  }, [messages, streaming]);

  const send = async () => {
    const text = input.trim();
    if (!text || streaming) return;
    setInput('');
    setStreaming(true);
    setMessages((s) => [...s, { role: 'user', content: text }, { role: 'assistant', content: '' }]);

    try {
      const token = localStorage.getItem('eg_admin_token');
      const res = await fetch(`${API}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token || ''}` },
        body: JSON.stringify({ mode: 'admin-writer', sessionId, message: text }),
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
          if (eventName === 'session') setSessionId(data);
          else if (eventName === 'error') toast({ title: 'AI error', description: data, variant: 'destructive' });
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
    } catch (e) {
      toast({ title: 'AI unavailable', description: e.message || 'Try again', variant: 'destructive' });
    } finally {
      setStreaming(false);
    }
  };

  const copyToClipboard = async (text, i) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(i);
      setTimeout(() => setCopied(-1), 1500);
    } catch (e) { /* ignore */ }
  };

  const applyInsertion = (text) => {
    if (onInsert) onInsert(text);
    toast({ title: 'Inserted', description: 'AI draft placed into the field.' });
    onClose();
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[110] flex items-center justify-center p-4 bg-[#1a1410]/60 backdrop-blur-sm">
      <div onClick={onClose} className="absolute inset-0" />
      <div className="relative w-full max-w-2xl bg-[#faf6f0] rounded-3xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
        <div className="bg-[#1a1410] text-[#faf6f0] px-6 py-4 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-[#c9a876]" />
            <span className="font-serif text-lg">Write with AI</span>
            <span className="text-[10px] tracking-[0.2em] uppercase bg-[#c9a876]/20 text-[#c9a876] px-2 py-0.5 rounded">Claude</span>
          </div>
          <button onClick={onClose} aria-label="Close" className="w-9 h-9 rounded-full hover:bg-[#241b15] flex items-center justify-center"><X className="w-4 h-4" /></button>
        </div>

        <div ref={bodyRef} className="flex-1 overflow-y-auto p-5 space-y-3 bg-[#faf6f0]">
          {messages.length === 0 && (
            <div className="text-sm text-[#5a4a3d] py-6">
              <p className="mb-3">Tell the assistant what to write. Examples:</p>
              <ul className="space-y-1.5 text-[#3d3128]">
                <li>&ldquo;Write a 2-sentence description for a lava-stone bracelet with amethyst.&rdquo;</li>
                <li>&ldquo;Draft an FAQ answer about caring for the bracelet in the shower.&rdquo;</li>
                <li>&ldquo;Rewrite this to sound warmer: [paste text]&rdquo;</li>
              </ul>
            </div>
          )}
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap ${m.role === 'user' ? 'bg-[#1a1410] text-[#faf6f0] rounded-br-sm' : 'bg-white text-[#2c2420] rounded-bl-sm border border-[#e8dfd1]'}`}>
                {m.content || (streaming && m.role === 'assistant' ? <Loader2 className="w-4 h-4 animate-spin text-[#8b6b4f]" /> : '')}
                {m.role === 'assistant' && m.content && !streaming && (
                  <div className="mt-3 pt-3 border-t border-[#e8dfd1] flex flex-wrap gap-2">
                    {onInsert && (
                      <button onClick={() => applyInsertion(m.content)} className="text-xs px-3 py-1.5 rounded-full bg-[#c9a876] text-[#1a1410] hover:bg-[#d6b885] font-medium">Use this</button>
                    )}
                    <button onClick={() => copyToClipboard(m.content, i)} className="text-xs px-3 py-1.5 rounded-full border border-[#e8dfd1] text-[#3d3128] hover:bg-[#faf6f0] inline-flex items-center gap-1">
                      {copied === i ? <><ClipboardCheck className="w-3 h-3" /> Copied</> : 'Copy'}
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        <div className="border-t border-[#e8dfd1] p-4 flex gap-2 items-end bg-white shrink-0">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) send(); }}
            placeholder="What would you like written?"
            rows={2}
            className="flex-1 resize-none max-h-40 px-4 py-2.5 border border-[#e8dfd1] rounded-2xl focus:border-[#6b4f3a] focus:outline-none text-sm bg-[#faf6f0]"
          />
          <button onClick={send} disabled={streaming || !input.trim()} aria-label="Send" className="w-11 h-11 rounded-full bg-[#1a1410] text-[#faf6f0] flex items-center justify-center hover:bg-[#6b4f3a] disabled:opacity-40 transition-colors shrink-0">
            {streaming ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          </button>
        </div>
      </div>
    </div>
  );
}
