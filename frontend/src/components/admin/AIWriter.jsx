import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Sparkles, X, Send, Loader2, ClipboardCheck, Undo2, History, Plus, Trash2, Pencil, Check, Mail, Wand2, MessageSquare } from 'lucide-react';
import api, { API } from '../../lib/api';
import { useToast } from '../../hooks/use-toast';
import { useSite } from '../../context/SiteContext';
import { chatAuthHeaders } from '../../lib/chatIdentity';

// One all-powerful admin AI. Given a single message the AI auto-decides:
//   • kind='chat'  → answer / draft copy (can be inserted into a field via `onInsert`)
//   • kind='edit'  → live site edit (auto-applied, with Undo)
//   • kind='email' → drafts a broadcast to all newsletter subscribers, admin confirms to send

export default function AIWriter({ open, onClose, onInsert, hint = '' }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [copied, setCopied] = useState(-1);
  const [showHistory, setShowHistory] = useState(false);
  const [sessions, setSessions] = useState([]);
  const [editingTitle, setEditingTitle] = useState(false);
  const [titleDraft, setTitleDraft] = useState('');
  const bodyRef = useRef(null);
  const { toast } = useToast();
  const { refresh } = useSite();

  const loadSessions = useCallback(async () => {
    try {
      const res = await fetch(`${API}/chat/sessions?mode=admin-writer`, { headers: chatAuthHeaders() });
      if (res.ok) setSessions(await res.json());
    } catch (e) { /* ignore */ }
  }, []);

  const loadSession = async (id) => {
    setShowHistory(false);
    try {
      const res = await fetch(`${API}/chat/session/${id}`, { headers: chatAuthHeaders() });
      if (!res.ok) throw new Error('Chat not found');
      const data = await res.json();
      setSessionId(data.id);
      setMessages((data.messages || []).map((m) => ({ role: m.role, kind: m.kind || 'text', content: m.content })));
    } catch (e) {
      toast({ title: 'Could not open chat', description: e.message, variant: 'destructive' });
    }
  };

  const newChat = () => {
    setSessionId(null);
    setMessages([]);
    setShowHistory(false);
  };

  const currentSession = sessions.find((s) => s.id === sessionId);

  useEffect(() => {
    if (open) {
      setMessages([]);
      setSessionId(null);
      setInput(hint || '');
      loadSessions();
    }
  }, [open, hint, loadSessions]);

  useEffect(() => {
    if (bodyRef.current) bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
  }, [messages, busy]);

  const send = async () => {
    const text = input.trim();
    if (!text || busy) return;
    setInput('');
    setBusy(true);
    setMessages((s) => [...s, { role: 'user', content: text }, { role: 'assistant', kind: 'pending', content: 'Thinking…' }]);
    try {
      const { data } = await api.post('/admin/ai', { message: text, sessionId });
      if (data.sessionId) setSessionId(data.sessionId);
      const kind = data.kind || 'chat';
      const msg = {
        role: 'assistant',
        kind,
        content: data.reply || '',
        applied: data.applied || [],
        failed: data.failed || [],
        snapshot: data.snapshot || null,
        emailDraft: data.emailDraft || null,
      };
      setMessages((s) => {
        const list = [...s];
        list[list.length - 1] = msg;
        return list;
      });
      if (kind === 'edit' && (data.applied || []).length > 0) {
        await refresh();
        // Also notify the AdminDashboard so it can show a global undo banner
        window.dispatchEvent(new CustomEvent('eg:ai-edit', {
          detail: { summary: data.reply, applied: data.applied, snapshot: data.snapshot, at: Date.now() }
        }));
        toast({ title: 'Site updated', description: data.reply || `Applied ${data.applied.length} change(s).` });
      } else if (kind === 'email' && data.emailDraft) {
        toast({ title: 'Draft ready', description: `Preview below, then confirm to send to ${data.emailDraft.recipientCount || 0} subscriber(s).` });
      }
    } catch (e) {
      const detail = e?.response?.data?.detail || e.message || 'Try again';
      setMessages((s) => {
        const list = [...s];
        list[list.length - 1] = { role: 'assistant', kind: 'error', content: `Error: ${detail}` };
        return list;
      });
      toast({ title: 'AI unavailable', description: detail, variant: 'destructive' });
    } finally {
      setBusy(false);
      loadSessions();
    }
  };

  const undo = async (snapshot, index) => {
    if (!snapshot) return;
    setBusy(true);
    try {
      await api.post('/admin/ai-edit/undo', { snapshot });
      await refresh();
      setMessages((s) => s.map((m, i) => (i === index ? { ...m, undone: true } : m)));
      window.dispatchEvent(new CustomEvent('eg:ai-edit-undone', { detail: {} }));
      toast({ title: 'Reverted', description: 'Site restored to the previous version.' });
    } catch (e) {
      toast({ title: 'Undo failed', description: e?.response?.data?.detail || e.message, variant: 'destructive' });
    } finally {
      setBusy(false);
    }
  };

  const sendBroadcast = async (draft, index) => {
    if (!draft?.subject || !draft?.html) return;
    if (!window.confirm(`Send this email to ${draft.recipientCount || 0} subscriber(s)?`)) return;
    setBusy(true);
    try {
      const { data } = await api.post('/admin/ai/email/send', { subject: draft.subject, html: draft.html });
      setMessages((s) => s.map((m, i) => (i === index ? { ...m, sent: true, sendStats: data } : m)));
      toast({ title: 'Email sent', description: `Delivered to ${data.sent} subscriber(s).${data.failed ? ` ${data.failed} failed.` : ''}` });
    } catch (e) {
      toast({ title: 'Send failed', description: e?.response?.data?.detail || e.message, variant: 'destructive' });
    } finally {
      setBusy(false);
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

  const deleteSession = async (id, e) => {
    e?.stopPropagation?.();
    if (!window.confirm('Delete this chat forever?')) return;
    try {
      await fetch(`${API}/chat/session/${id}`, { method: 'DELETE', headers: chatAuthHeaders() });
      if (sessionId === id) newChat();
      loadSessions();
    } catch (err) { /* ignore */ }
  };

  const startRename = () => {
    if (!currentSession) return;
    setTitleDraft(currentSession.title || '');
    setEditingTitle(true);
  };

  const saveRename = async () => {
    if (!sessionId) { setEditingTitle(false); return; }
    const t = titleDraft.trim();
    if (!t) { setEditingTitle(false); return; }
    try {
      await fetch(`${API}/chat/session/${sessionId}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json', ...chatAuthHeaders() },
        body: JSON.stringify({ title: t }),
      });
      loadSessions();
      setEditingTitle(false);
    } catch (err) { /* ignore */ }
  };

  const onKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  if (!open) return null;

  const kindIcon = (k) => k === 'edit' ? <Wand2 className="w-3 h-3" /> : k === 'email' ? <Mail className="w-3 h-3" /> : <MessageSquare className="w-3 h-3" />;
  const kindLabel = (k) => k === 'edit' ? 'Site edit' : k === 'email' ? 'Email draft' : 'Reply';

  return (
    <div className="fixed inset-0 z-[110] flex items-center justify-center p-4 bg-[#1a1410]/60 backdrop-blur-sm">
      <div onClick={onClose} className="absolute inset-0" />
      <div className="relative w-full max-w-2xl bg-[#faf6f0] rounded-3xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh]" data-testid="admin-ai-panel">
        <div className="bg-[#1a1410] text-[#faf6f0] px-6 pt-4 pb-3 shrink-0">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2 min-w-0">
              <Sparkles className="w-4 h-4 text-[#c9a876] shrink-0" />
              {editingTitle && sessionId ? (
                <div className="flex items-center gap-1 flex-1">
                  <input value={titleDraft} onChange={(e) => setTitleDraft(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') saveRename(); if (e.key === 'Escape') setEditingTitle(false); }} autoFocus className="flex-1 px-2 py-1 bg-[#241b15] text-[#faf6f0] rounded text-sm outline-none border border-[#3d2f24]" />
                  <button onClick={saveRename} className="text-[#c9a876] hover:text-[#faf6f0]" aria-label="Save"><Check className="w-3.5 h-3.5" /></button>
                </div>
              ) : (
                <>
                  <span className="font-serif text-lg truncate">{sessionId ? (currentSession?.title || 'Admin AI') : 'Admin AI'}</span>
                  <span className="text-[10px] tracking-[0.2em] uppercase bg-[#c9a876]/20 text-[#c9a876] px-2 py-0.5 rounded shrink-0">Claude</span>
                  {sessionId && <button onClick={startRename} className="text-[#8b6b4f] hover:text-[#c9a876] shrink-0" aria-label="Rename"><Pencil className="w-3 h-3" /></button>}
                </>
              )}
            </div>
            <div className="flex items-center gap-1 shrink-0">
              <button onClick={() => setShowHistory(!showHistory)} title="History" aria-label="History" data-testid="admin-ai-history" className={`w-8 h-8 rounded-full flex items-center justify-center transition-colors ${showHistory ? 'bg-[#c9a876] text-[#1a1410]' : 'hover:bg-[#241b15]'}`}><History className="w-4 h-4" /></button>
              <button onClick={newChat} title="New chat" aria-label="New chat" data-testid="admin-ai-new" className="w-8 h-8 rounded-full hover:bg-[#241b15] flex items-center justify-center"><Plus className="w-4 h-4" /></button>
              <button onClick={onClose} aria-label="Close" data-testid="admin-ai-close" className="w-9 h-9 rounded-full hover:bg-[#241b15] flex items-center justify-center"><X className="w-4 h-4" /></button>
            </div>
          </div>
          <p className="text-[11px] text-[#8b6b4f] mt-2">One AI · chat, draft copy, edit the site, or email your subscribers — just ask.</p>
        </div>

        <div ref={bodyRef} className="flex-1 overflow-y-auto p-5 space-y-3 bg-[#faf6f0] relative">
          {showHistory && (
            <div className="absolute inset-0 bg-[#faf6f0] z-10 overflow-y-auto" data-testid="admin-ai-history-list">
              <div className="p-3 border-b border-[#e8dfd1] flex items-center justify-between">
                <p className="text-xs tracking-[0.2em] uppercase text-[#8b6b4f]">Your chats</p>
                <button onClick={newChat} className="text-xs px-3 py-1 rounded-full bg-[#1a1410] text-[#faf6f0] inline-flex items-center gap-1"><Plus className="w-3 h-3" /> New</button>
              </div>
              {sessions.length === 0 ? (
                <p className="text-center text-sm text-[#8b6b4f] italic p-8">No saved chats yet.</p>
              ) : (
                <div className="divide-y divide-[#e8dfd1]">
                  {sessions.map((s) => (
                    <button key={s.id} onClick={() => loadSession(s.id)} className={`w-full text-left px-4 py-3 flex items-start justify-between gap-3 group hover:bg-white ${s.id === sessionId ? 'bg-white' : ''}`}>
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
          )}
          {messages.length === 0 && !showHistory && (
            <div className="text-sm text-[#5a4a3d] py-6" data-testid="admin-ai-empty">
              <p className="mb-3">Ask anything. I&rsquo;ll pick the right action automatically:</p>
              <ul className="space-y-2 text-[#3d3128]">
                <li><MessageSquare className="w-3 h-3 inline mr-1 text-[#8b6b4f]" /> &ldquo;Draft a warm 2-sentence description for an amethyst bracelet.&rdquo;</li>
                <li><Wand2 className="w-3 h-3 inline mr-1 text-[#c9a876]" /> &ldquo;Change the hero subtitle to sound more inviting.&rdquo;</li>
                <li><Mail className="w-3 h-3 inline mr-1 text-[#6b4f3a]" /> &ldquo;Email my subscribers announcing our new Sunstone Ember bracelet.&rdquo;</li>
              </ul>
            </div>
          )}
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`} data-testid={`admin-ai-msg-${i}`}>
              <div className={`max-w-[90%] rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap ${m.role === 'user' ? 'bg-[#1a1410] text-[#faf6f0] rounded-br-sm' : 'bg-white text-[#2c2420] rounded-bl-sm border border-[#e8dfd1]'}`}>
                {m.role === 'assistant' && m.kind && m.kind !== 'pending' && m.kind !== 'error' && (
                  <div className="mb-2 inline-flex items-center gap-1.5 text-[10px] tracking-[0.15em] uppercase text-[#8b6b4f] bg-[#faf6f0] rounded-full px-2 py-0.5">
                    {kindIcon(m.kind)} {kindLabel(m.kind)}
                  </div>
                )}
                {m.kind === 'pending' ? (
                  <div className="flex items-center gap-2 text-[#8b6b4f]"><Loader2 className="w-4 h-4 animate-spin" /> {m.content}</div>
                ) : (
                  <div>{m.content}</div>
                )}

                {/* Chat/reply: offer Copy + Use this */}
                {m.role === 'assistant' && m.kind === 'chat' && m.content && (
                  <div className="mt-3 pt-3 border-t border-[#e8dfd1] flex flex-wrap gap-2">
                    {onInsert && <button onClick={() => applyInsertion(m.content)} data-testid={`admin-ai-use-${i}`} className="text-xs px-3 py-1.5 rounded-full bg-[#c9a876] text-[#1a1410] hover:bg-[#d6b885] font-medium">Use this</button>}
                    <button onClick={() => copyToClipboard(m.content, i)} className="text-xs px-3 py-1.5 rounded-full border border-[#e8dfd1] text-[#3d3128] hover:bg-[#faf6f0] inline-flex items-center gap-1">
                      {copied === i ? <><ClipboardCheck className="w-3 h-3" /> Copied</> : 'Copy'}
                    </button>
                  </div>
                )}

                {/* Edit: applied paths + Undo */}
                {m.role === 'assistant' && m.kind === 'edit' && (
                  <div className="mt-3 pt-3 border-t border-[#e8dfd1] space-y-2">
                    {(m.applied || []).length > 0 && (
                      <details className="text-xs" open>
                        <summary className="cursor-pointer text-[#6b4f3a]">{m.applied.length} change{m.applied.length === 1 ? '' : 's'} applied</summary>
                        <ul className="mt-1.5 space-y-1 text-[#5a4a3d]">
                          {m.applied.map((a, k) => (
                            <li key={k} className="font-mono text-[11px] bg-[#faf6f0] px-2 py-1 rounded truncate"><span className="text-[#c9a876]">→</span> {a.path}</li>
                          ))}
                        </ul>
                      </details>
                    )}
                    {(m.failed || []).length > 0 && (
                      <details className="text-xs">
                        <summary className="cursor-pointer text-red-700">{m.failed.length} rejected</summary>
                        <ul className="mt-1.5 space-y-1 text-[11px] text-red-700">
                          {m.failed.map((f, k) => <li key={k}>{f.reason}</li>)}
                        </ul>
                      </details>
                    )}
                    {m.snapshot && !m.undone && (m.applied || []).length > 0 && (
                      <button onClick={() => undo(m.snapshot, i)} disabled={busy} data-testid={`admin-ai-undo-${i}`} className="text-xs px-3 py-1.5 rounded-full border border-[#3d3128] text-[#3d3128] hover:bg-[#3d3128] hover:text-[#faf6f0] inline-flex items-center gap-1 disabled:opacity-60">
                        <Undo2 className="w-3 h-3" /> Undo
                      </button>
                    )}
                    {m.undone && <span className="text-xs text-[#8b6b4f] italic">Reverted</span>}
                  </div>
                )}

                {/* Email draft: preview + Send */}
                {m.role === 'assistant' && m.kind === 'email' && m.emailDraft && (
                  <div className="mt-3 pt-3 border-t border-[#e8dfd1] space-y-3">
                    <div className="text-[11px] text-[#8b6b4f] uppercase tracking-wider">Subject</div>
                    <div className="text-sm text-[#1a1410] font-medium -mt-2">{m.emailDraft.subject}</div>
                    <div className="text-[11px] text-[#8b6b4f] uppercase tracking-wider">Preview</div>
                    <div className="border border-[#e8dfd1] rounded-lg bg-white max-h-64 overflow-y-auto -mt-2">
                      <div className="p-2" dangerouslySetInnerHTML={{ __html: m.emailDraft.html }} />
                    </div>
                    {!m.sent ? (
                      <button
                        onClick={() => sendBroadcast(m.emailDraft, i)}
                        disabled={busy}
                        data-testid={`admin-ai-send-email-${i}`}
                        className="text-xs px-4 py-2 rounded-full bg-[#1a1410] text-[#faf6f0] hover:bg-[#6b4f3a] inline-flex items-center gap-1.5 disabled:opacity-60">
                        <Mail className="w-3 h-3" /> Send to {m.emailDraft.recipientCount} subscriber{m.emailDraft.recipientCount === 1 ? '' : 's'}
                      </button>
                    ) : (
                      <div className="text-xs text-[#3d3128] italic">
                        Sent to {m.sendStats?.sent || 0} subscriber(s){m.sendStats?.failed ? ` — ${m.sendStats.failed} failed` : ''}.
                      </div>
                    )}
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
            onKeyDown={onKey}
            placeholder="Ask anything — I'll chat, draft, edit the site, or email your subscribers."
            rows={2}
            data-testid="admin-ai-input"
            className="flex-1 resize-none max-h-40 px-4 py-2.5 border border-[#e8dfd1] rounded-2xl focus:border-[#6b4f3a] focus:outline-none text-sm bg-[#faf6f0]"
          />
          <button onClick={send} disabled={busy || !input.trim()} aria-label="Send" data-testid="admin-ai-send" className="w-11 h-11 rounded-full bg-[#1a1410] text-[#faf6f0] flex items-center justify-center hover:bg-[#6b4f3a] disabled:opacity-40 transition-colors shrink-0">
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          </button>
        </div>
        <p className="text-[10px] text-[#8b6b4f] text-center py-2 bg-[#faf6f0]">Site edits apply immediately and can be undone. Emails are sent only after you confirm.</p>
      </div>
    </div>
  );
}
