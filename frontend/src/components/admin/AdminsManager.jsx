import React, { useEffect, useState } from 'react';
import { Trash2, Plus, Save, ShieldCheck, RefreshCw, KeyRound, ShieldOff, Mail, Pencil, X, Copy, Download, Check, Loader2 } from 'lucide-react';
import api from '../../lib/api';
import { useToast } from '../../hooks/use-toast';
import { Field, TextInput } from './FormControls';
import { pwdIssues, PWD_MSG } from '../../pages/AdminLogin';

const SECTION_LABELS = {
  navbar: 'Navigation Menu',
  hero: 'Hero',
  products: 'Collection (Products)',
  story: 'Our Story',
  promise: 'Our Promise',
  chakra: 'Chakra Guide',
  stats: 'Best Sellers (Stats)',
  lavaMeaning: 'What Lava Stone Means',
  founder: 'Meet the Founder',
  craft: 'Craftsmanship',
  faq: 'FAQ',
  gallery: 'Gallery',
  vip: 'VIP Membership',
  footer: 'Footer & Contact',
  sectionOrder: 'Section order',
  sectionVisibility: 'Section show/hide',
  manage_admins: 'Manage admins',
  manage_subscribers: 'Newsletter subscribers',
  manage_users: 'Members (users)',
};

export default function AdminsManager({ currentUser }) {
  const [admins, setAdmins] = useState([]);
  const [perms, setPerms] = useState({ sectionPermissions: [], metaPermissions: [], all: [] });
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [newAdmin, setNewAdmin] = useState({ username: '', email: '', password: '', permissions: [], isSuper: false });
  const { toast } = useToast();

  const load = async () => {
    setLoading(true);
    try {
      const [a, p] = await Promise.all([api.get('/admin/admins'), api.get('/permissions')]);
      setAdmins(a.data);
      setPerms(p.data);
    } catch (e) {
      toast({ title: 'Failed to load admins', description: e?.response?.data?.detail || e.message, variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  useEffect(() => {
    const handler = () => load();
    window.addEventListener('eg:admin-managed', handler);
    return () => window.removeEventListener('eg:admin-managed', handler);
  }, []);

  const toggleNewPerm = (k) => {
    setNewAdmin((s) => ({
      ...s,
      permissions: s.permissions.includes(k)
        ? s.permissions.filter((x) => x !== k)
        : [...s.permissions, k],
    }));
  };

  const create = async () => {
    if (!newAdmin.username.trim() || !newAdmin.password) {
      toast({ title: 'Missing info', description: 'Username and password are required.', variant: 'destructive' });
      return;
    }
    const email = (newAdmin.email || '').trim();
    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      toast({ title: 'Email required', description: 'Enter a valid email so they can receive 2FA codes.', variant: 'destructive' });
      return;
    }
    const issues = pwdIssues(newAdmin.password);
    if (issues.length) {
      toast({ title: 'Weak password', description: issues.join(' \u00b7 '), variant: 'destructive' });
      return;
    }
    setCreating(true);
    try {
      await api.post('/admin/admins', { ...newAdmin, email });
      toast({ title: 'Admin created', description: `${newAdmin.username} can sign in and will be prompted to enroll in 2FA on first login.` });
      setNewAdmin({ username: '', email: '', password: '', permissions: [], isSuper: false });
      load();
    } catch (e) {
      toast({ title: 'Could not create', description: e?.response?.data?.detail || e.message, variant: 'destructive' });
    } finally {
      setCreating(false);
    }
  };

  const updateEmail = async (a, newEmail) => {
    const email = (newEmail || '').trim();
    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      toast({ title: 'Invalid email', description: 'Enter a valid email address.', variant: 'destructive' });
      return false;
    }
    try {
      await api.put(`/admin/admins/${a.id}`, { email });
      toast({ title: 'Email updated', description: `${a.username} \u2192 ${email}` });
      load();
      return true;
    } catch (e) {
      toast({ title: 'Update failed', description: e?.response?.data?.detail || e.message, variant: 'destructive' });
      return false;
    }
  };

  const updatePerms = async (a, permissions) => {
    try {
      await api.put(`/admin/admins/${a.id}`, { permissions });
      toast({ title: 'Permissions updated', description: a.username });
      load();
    } catch (e) {
      toast({ title: 'Update failed', description: e?.response?.data?.detail || e.message, variant: 'destructive' });
    }
  };

  const setSuper = async (a, isSuper) => {
    try {
      await api.put(`/admin/admins/${a.id}`, { isSuper });
      toast({ title: isSuper ? 'Granted super admin' : 'Removed super admin', description: a.username });
      load();
    } catch (e) {
      toast({ title: 'Update failed', description: e?.response?.data?.detail || e.message, variant: 'destructive' });
    }
  };

  const resetPassword = async (a) => {
    const pw = window.prompt(`New password for ${a.username}:\n\n${PWD_MSG}`);
    if (!pw) return;
    const issues = pwdIssues(pw);
    if (issues.length) {
      toast({ title: 'Weak password', description: issues.join(' · '), variant: 'destructive' });
      return;
    }
    try {
      await api.put(`/admin/admins/${a.id}`, { password: pw });
      toast({ title: 'Password updated', description: a.username });
    } catch (e) {
      toast({ title: 'Update failed', description: e?.response?.data?.detail || e.message, variant: 'destructive' });
    }
  };

  const reset2fa = async (a) => {
    if (!window.confirm(`Reset 2FA for "${a.username}"?\nThey'll be asked to enroll again on their next login.`)) return;
    try {
      await api.post(`/admin/2fa/reset/${a.id}`);
      toast({ title: '2FA reset', description: `${a.username} will re-enroll on next login.` });
      load();
    } catch (e) {
      toast({ title: 'Reset failed', description: e?.response?.data?.detail || e.message, variant: 'destructive' });
    }
  };

  const removeAdmin = async (a) => {
    if (!window.confirm(`Delete admin "${a.username}"? This cannot be undone.`)) return;
    try {
      await api.delete(`/admin/admins/${a.id}`);
      toast({ title: 'Deleted', description: a.username });
      load();
    } catch (e) {
      toast({ title: 'Delete failed', description: e?.response?.data?.detail || e.message, variant: 'destructive' });
    }
  };

  if (loading) {
    return <div className="flex items-center gap-2 text-[#6b4f3a] text-sm"><RefreshCw className="w-4 h-4 animate-spin" /> Loading admins…</div>;
  }

  return (
    <div className="space-y-6">
      <p className="text-sm text-[#5a4a3d]">Create additional admins and choose exactly which sections each one can edit. <strong>Super admins</strong> can do everything (including managing other admins).</p>

      {/* Existing admins */}
      <div className="space-y-4">
        {admins.length === 0 && <p className="text-sm text-[#8b6b4f] italic">No additional admins yet.</p>}
        {admins.map((a) => (
          <AdminRow
            key={a.id}
            admin={a}
            allPerms={perms.all}
            onUpdatePerms={(p) => updatePerms(a, p)}
            onSetSuper={(s) => setSuper(a, s)}
            onUpdateEmail={(v) => updateEmail(a, v)}
            onResetPassword={() => resetPassword(a)}
            onReset2fa={() => reset2fa(a)}
            onRemove={() => removeAdmin(a)}
            isCurrentUser={currentUser?.id === a.id}
          />
        ))}
      </div>

      {/* Create new */}
      <div className="border border-[#e8dfd1] rounded-2xl p-5 bg-[#faf6f0]">
        <h4 className="font-serif text-lg text-[#1a1410] mb-4 flex items-center gap-2"><Plus className="w-4 h-4" /> Add new admin</h4>
        <div className="grid sm:grid-cols-2 gap-3 mb-2">
          <Field label="Username"><TextInput value={newAdmin.username} onChange={(v) => setNewAdmin({ ...newAdmin, username: v })} placeholder="e.g. mom" data-testid="new-admin-username" /></Field>
          <Field label="Email (required)"><TextInput value={newAdmin.email} onChange={(v) => setNewAdmin({ ...newAdmin, email: v })} placeholder="mom@example.com" type="email" data-testid="new-admin-email" /></Field>
        </div>
        <Field label="Password"><TextInput value={newAdmin.password} onChange={(v) => setNewAdmin({ ...newAdmin, password: v })} placeholder="choose a strong password" type="text" data-testid="new-admin-password" /></Field>
        <PasswordChecklist password={newAdmin.password} />
        <p className="text-xs text-[#8b6b4f] mt-3 mb-4"><ShieldCheck className="w-3 h-3 inline mr-1" /> They\u2019ll set up an authenticator app on first login, and can also receive 2FA codes at this email.</p>
        <label className="flex items-center gap-2 text-sm text-[#3d3128] mb-4 cursor-pointer">
          <input type="checkbox" checked={newAdmin.isSuper} onChange={(e) => setNewAdmin({ ...newAdmin, isSuper: e.target.checked })} className="rounded" />
          <ShieldCheck className="w-4 h-4 text-[#c9a876]" /> Super admin (full access, can manage other admins)
        </label>
        {!newAdmin.isSuper && (
          <div>
            <p className="text-xs tracking-[0.2em] uppercase text-[#8b6b4f] mb-2">Allowed sections</p>
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-2">
              {perms.all.map((k) => (
                <label key={k} className="flex items-center gap-2 text-sm text-[#3d3128] cursor-pointer">
                  <input type="checkbox" checked={newAdmin.permissions.includes(k)} onChange={() => toggleNewPerm(k)} className="rounded" />
                  {SECTION_LABELS[k] || k}
                </label>
              ))}
            </div>
          </div>
        )}
        <button onClick={create} disabled={creating} className="mt-5 inline-flex items-center gap-2 px-5 py-2.5 bg-[#1a1410] text-[#faf6f0] rounded-full text-sm hover:bg-[#6b4f3a] disabled:opacity-60">
          {creating ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />} Create admin
        </button>
      </div>
    </div>
  );
}

function PasswordChecklist({ password }) {
  const items = [
    { ok: (password || '').length >= 8, label: 'At least 8 characters' },
    { ok: /[A-Z]/.test(password || ''), label: 'One uppercase letter' },
    { ok: /[a-z]/.test(password || ''), label: 'One lowercase letter' },
    { ok: /[0-9]/.test(password || ''), label: 'One number' },
    { ok: /[^A-Za-z0-9]/.test(password || ''), label: 'One symbol' },
  ];
  if (!password) return null;
  return (
    <ul className="text-xs grid sm:grid-cols-2 gap-x-4 gap-y-1 mb-1 mt-1" data-testid="password-checklist">
      {items.map((it) => (
        <li key={it.label} className={it.ok ? 'text-green-800' : 'text-[#8b6b4f]'}>
          <span className="inline-block w-4">{it.ok ? '\u2713' : '\u2022'}</span> {it.label}
        </li>
      ))}
    </ul>
  );
}

function AdminRow({ admin, allPerms, onUpdatePerms, onSetSuper, onUpdateEmail, onResetPassword, onReset2fa, onRemove, isCurrentUser }) {
  const [permissions, setPermissions] = useState(admin.permissions || []);
  const [editing, setEditing] = useState(false);
  const [emailEditing, setEmailEditing] = useState(false);
  const [emailValue, setEmailValue] = useState(admin.email || '');
  const dirty = JSON.stringify([...permissions].sort()) !== JSON.stringify([...(admin.permissions || [])].sort());

  const toggle = (k) => {
    setPermissions((s) => s.includes(k) ? s.filter((x) => x !== k) : [...s, k]);
  };

  const saveEmail = async () => {
    const ok = await onUpdateEmail(emailValue);
    if (ok) setEmailEditing(false);
  };

  return (
    <div className="border border-[#e8dfd1] rounded-2xl p-5 bg-white">
      <div className="flex items-start justify-between gap-3 mb-3 flex-wrap">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-serif text-lg text-[#1a1410]">{admin.username}</span>
            {admin.isSuper && <span className="inline-flex items-center gap-1 text-xs bg-[#c9a876]/20 text-[#6b4f3a] px-2 py-0.5 rounded-full"><ShieldCheck className="w-3 h-3" /> super</span>}
            {admin.twoFactorEnabled ? (
              <span className="inline-flex items-center gap-1 text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded-full" data-testid="admin-row-2fa-on"><ShieldCheck className="w-3 h-3" /> 2FA on</span>
            ) : (
              <span className="inline-flex items-center gap-1 text-xs bg-amber-100 text-amber-800 px-2 py-0.5 rounded-full" data-testid="admin-row-2fa-off"><ShieldOff className="w-3 h-3" /> 2FA pending</span>
            )}
            {isCurrentUser && <span className="text-xs text-[#8b6b4f]">(you)</span>}
          </div>
          <div className="flex items-center gap-2 mt-1" data-testid={`admin-row-email-${admin.id}`}>
            <Mail className="w-3 h-3 text-[#8b6b4f]" />
            {emailEditing ? (
              <>
                <input
                  type="email"
                  value={emailValue}
                  onChange={(e) => setEmailValue(e.target.value)}
                  className="text-xs px-2 py-1 border border-[#e8dfd1] rounded-lg bg-[#faf6f0] focus:outline-none focus:border-[#6b4f3a] w-56"
                  data-testid={`admin-row-email-input-${admin.id}`}
                  autoFocus
                />
                <button onClick={saveEmail} className="text-xs px-2 py-1 bg-[#1a1410] text-[#faf6f0] rounded-md hover:bg-[#6b4f3a]" data-testid={`admin-row-email-save-${admin.id}`}><Save className="w-3 h-3" /></button>
                <button onClick={() => { setEmailEditing(false); setEmailValue(admin.email || ''); }} className="text-xs px-2 py-1 border border-[#e8dfd1] rounded-md hover:bg-[#faf6f0]"><X className="w-3 h-3" /></button>
              </>
            ) : (
              <>
                <span className="text-xs text-[#5a4a3d]">{admin.email || <em className="text-[#c17b5c]">no email set</em>}</span>
                <button onClick={() => setEmailEditing(true)} className="text-xs px-1.5 py-0.5 text-[#6b4f3a] hover:text-[#1a1410] inline-flex items-center gap-0.5" data-testid={`admin-row-edit-email-${admin.id}`} title="Edit email"><Pencil className="w-3 h-3" /></button>
              </>
            )}
          </div>
          {admin.createdAt && <p className="text-xs text-[#8b6b4f] mt-1">Created {new Date(admin.createdAt).toLocaleDateString()}</p>}
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <button onClick={onResetPassword} className="text-xs px-3 py-1.5 border border-[#e8dfd1] rounded-lg hover:bg-[#faf6f0] inline-flex items-center gap-1"><KeyRound className="w-3 h-3" /> Reset password</button>
          {isCurrentUser && admin.twoFactorEnabled && <BackupCodesButton />}
          {!isCurrentUser && admin.twoFactorEnabled && (
            <button onClick={onReset2fa} data-testid={`admin-row-reset-2fa-${admin.id}`} className="text-xs px-3 py-1.5 border border-[#e8dfd1] rounded-lg hover:bg-[#faf6f0] inline-flex items-center gap-1"><ShieldOff className="w-3 h-3" /> Reset 2FA</button>
          )}
          {!isCurrentUser && (
            <button onClick={onRemove} className="text-xs px-3 py-1.5 border border-red-300 text-red-700 rounded-lg hover:bg-red-50 inline-flex items-center gap-1"><Trash2 className="w-3 h-3" /> Delete</button>
          )}
        </div>
      </div>

      <label className="flex items-center gap-2 text-sm text-[#3d3128] cursor-pointer mb-3">
        <input type="checkbox" checked={admin.isSuper} onChange={(e) => onSetSuper(e.target.checked)} className="rounded" disabled={isCurrentUser && admin.isSuper} />
        Super admin (full access)
      </label>

      {!admin.isSuper && (
        <div>
          <button onClick={() => setEditing(!editing)} className="text-xs text-[#6b4f3a] underline mb-2">{editing ? 'Hide permissions' : `Edit permissions (${admin.permissions?.length || 0})`}</button>
          {editing && (
            <div className="border-t border-[#e8dfd1] pt-3 mt-1">
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-2 mb-3">
                {allPerms.map((k) => (
                  <label key={k} className="flex items-center gap-2 text-sm text-[#3d3128] cursor-pointer">
                    <input type="checkbox" checked={permissions.includes(k)} onChange={() => toggle(k)} className="rounded" />
                    {SECTION_LABELS[k] || k}
                  </label>
                ))}
              </div>
              <button onClick={() => { onUpdatePerms(permissions); setEditing(false); }} disabled={!dirty} className="inline-flex items-center gap-2 px-4 py-2 text-xs bg-[#1a1410] text-[#faf6f0] rounded-full hover:bg-[#6b4f3a] disabled:opacity-50">
                <Save className="w-3 h-3" /> Save permissions
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}


function BackupCodesButton() {
  const { toast } = useToast();
  const [open, setOpen] = useState(false);
  const [remaining, setRemaining] = useState(null);
  const [code, setCode] = useState('');
  const [busy, setBusy] = useState(false);
  const [codes, setCodes] = useState(null);
  const [copied, setCopied] = useState(false);

  const loadRemaining = async () => {
    try {
      const { data } = await api.get('/admin/2fa/backup-codes');
      setRemaining(data.remaining);
    } catch (e) { /* ignore */ }
  };

  useEffect(() => { loadRemaining(); }, []);

  const openModal = () => {
    setCode('');
    setCodes(null);
    setCopied(false);
    setOpen(true);
  };

  const closeModal = () => {
    setOpen(false);
    if (codes) loadRemaining();
  };

  const generate = async () => {
    const c = code.trim();
    if (c.length < 6 || busy) return;
    setBusy(true);
    try {
      const { data } = await api.post('/admin/2fa/backup-codes/regenerate', { code: c });
      setCodes(data.backupCodes || []);
      toast({ title: 'New backup codes ready', description: 'Save them now — your old codes no longer work.' });
    } catch (e) {
      toast({ title: 'Couldn\u2019t regenerate', description: e?.response?.data?.detail || 'Check your authenticator code and try again.', variant: 'destructive' });
    } finally {
      setBusy(false);
    }
  };

  const copyAll = async () => {
    try {
      await navigator.clipboard.writeText((codes || []).join('\n'));
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch (e) { /* ignore */ }
  };

  const download = () => {
    const blob = new Blob([`Essential Gemstones \u2014 admin backup codes\n\n${(codes || []).join('\n')}\n`], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'essential-gemstones-backup-codes.txt';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <>
      <button
        onClick={openModal}
        data-testid="regenerate-backup-codes-btn"
        className="text-xs px-3 py-1.5 border border-[#e8dfd1] rounded-lg hover:bg-[#faf6f0] inline-flex items-center gap-1"
        title="Generate a fresh set of one-time backup codes"
      >
        <RefreshCw className="w-3 h-3" /> Regenerate backup codes
        {remaining !== null && <span className="ml-0.5 text-[#8b6b4f]">({remaining} left)</span>}
      </button>

      {open && (
        <div className="fixed inset-0 z-[120] flex items-center justify-center p-4 bg-[#1a1410]/60 backdrop-blur-sm" data-testid="backup-codes-modal">
          <div onClick={closeModal} className="absolute inset-0" />
          <div className="relative w-full max-w-md bg-[#faf6f0] rounded-3xl shadow-2xl overflow-hidden">
            <div className="bg-[#1a1410] text-[#faf6f0] px-6 py-4 flex items-center justify-between">
              <span className="font-serif text-lg inline-flex items-center gap-2"><KeyRound className="w-4 h-4 text-[#c9a876]" /> Backup codes</span>
              <button onClick={closeModal} aria-label="Close" data-testid="backup-codes-close" className="w-8 h-8 rounded-full hover:bg-[#241b15] flex items-center justify-center"><X className="w-4 h-4" /></button>
            </div>

            <div className="p-6">
              {!codes ? (
                <>
                  <p className="text-sm text-[#5a4a3d] mb-4">
                    Generating new codes will <strong className="text-[#1a1410]">invalidate all your existing backup codes</strong>. Enter the current 6-digit code from your authenticator app to confirm.
                  </p>
                  <input
                    value={code}
                    onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                    onKeyDown={(e) => { if (e.key === 'Enter') generate(); }}
                    inputMode="numeric"
                    autoFocus
                    placeholder="123456"
                    data-testid="backup-codes-totp-input"
                    className="w-full text-center tracking-[0.5em] text-lg px-4 py-3 border border-[#e8dfd1] rounded-2xl bg-white focus:outline-none focus:border-[#6b4f3a] font-mono"
                  />
                  <button
                    onClick={generate}
                    disabled={busy || code.trim().length < 6}
                    data-testid="backup-codes-generate"
                    className="mt-4 w-full inline-flex items-center justify-center gap-2 px-5 py-3 bg-[#1a1410] text-[#faf6f0] rounded-full text-sm hover:bg-[#6b4f3a] disabled:opacity-50"
                  >
                    {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />} Generate new codes
                  </button>
                </>
              ) : (
                <>
                  <p className="text-sm text-[#5a4a3d] mb-4">
                    Save these somewhere safe. Each code works once. They <strong className="text-[#1a1410]">won\u2019t be shown again</strong>.
                  </p>
                  <div className="grid grid-cols-2 gap-2 mb-4" data-testid="backup-codes-list">
                    {codes.map((c, i) => (
                      <code key={i} className="font-mono text-sm bg-white border border-[#e8dfd1] rounded-lg px-3 py-2 text-center text-[#1a1410] select-all">{c}</code>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <button onClick={copyAll} data-testid="backup-codes-copy" className="flex-1 inline-flex items-center justify-center gap-1.5 px-4 py-2.5 border border-[#e8dfd1] rounded-full text-sm hover:bg-white">
                      {copied ? <><Check className="w-4 h-4" /> Copied</> : <><Copy className="w-4 h-4" /> Copy all</>}
                    </button>
                    <button onClick={download} data-testid="backup-codes-download" className="flex-1 inline-flex items-center justify-center gap-1.5 px-4 py-2.5 border border-[#e8dfd1] rounded-full text-sm hover:bg-white">
                      <Download className="w-4 h-4" /> Download
                    </button>
                  </div>
                  <button onClick={closeModal} data-testid="backup-codes-done" className="mt-3 w-full px-5 py-2.5 bg-[#1a1410] text-[#faf6f0] rounded-full text-sm hover:bg-[#6b4f3a]">Done</button>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
