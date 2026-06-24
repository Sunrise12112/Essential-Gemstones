import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Lock, Gem, User } from 'lucide-react';
import api from '../lib/api';
import { useToast } from '../hooks/use-toast';

export default function AdminLogin() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { toast } = useToast();

  useEffect(() => {
    if (localStorage.getItem('eg_admin_token')) {
      navigate('/admin/dashboard');
    }
  }, [navigate]);

  const onSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const body = username ? { username, password } : { password };
      const { data } = await api.post('/admin/login', body);
      localStorage.setItem('eg_admin_token', data.token);
      if (data.user) localStorage.setItem('eg_admin_user', JSON.stringify(data.user));
      navigate('/admin/dashboard');
    } catch (err) {
      toast({ title: 'Login failed', description: 'Incorrect username or password.', variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#faf6f0] flex items-center justify-center px-6">
      <form onSubmit={onSubmit} className="w-full max-w-md bg-white rounded-3xl border border-[#e8dfd1] p-10 shadow-xl">
        <div className="flex items-center gap-2 mb-2 text-[#6b4f3a]">
          <Gem className="w-5 h-5" />
          <span className="font-serif text-xl text-[#2c2420]">Essential Gemstones</span>
        </div>
        <h1 className="font-serif text-3xl text-[#1a1410] mb-2">Admin Login</h1>
        <p className="text-sm text-[#5a4a3d] mb-8">Sign in to manage the site.</p>

        <label className="block text-xs tracking-[0.2em] uppercase text-[#8b6b4f] mb-2">Username <span className="text-[#bfae95] normal-case tracking-normal">(leave blank for master)</span></label>
        <div className="relative mb-5">
          <User className="w-4 h-4 absolute left-4 top-1/2 -translate-y-1/2 text-[#8b6b4f]" />
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            className="w-full pl-11 pr-4 py-3.5 border border-[#e8dfd1] rounded-full focus:border-[#6b4f3a] focus:outline-none bg-[#faf6f0]"
            placeholder="optional"
          />
        </div>

        <label className="block text-xs tracking-[0.2em] uppercase text-[#8b6b4f] mb-2">Password</label>
        <div className="relative mb-6">
          <Lock className="w-4 h-4 absolute left-4 top-1/2 -translate-y-1/2 text-[#8b6b4f]" />
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoFocus
            autoComplete="current-password"
            className="w-full pl-11 pr-4 py-3.5 border border-[#e8dfd1] rounded-full focus:border-[#6b4f3a] focus:outline-none bg-[#faf6f0]"
            placeholder="\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022"
          />
        </div>
        <button type="submit" disabled={loading} className="w-full py-3.5 bg-[#1a1410] text-[#faf6f0] rounded-full text-sm tracking-wider uppercase hover:bg-[#6b4f3a] transition-colors disabled:opacity-60">
          {loading ? 'Signing in\u2026' : 'Sign in'}
        </button>
      </form>
    </div>
  );
}
