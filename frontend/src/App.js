import React, { useEffect } from 'react';
import './App.css';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Home from './pages/Home';
import AdminLogin from './pages/AdminLogin';
import AdminDashboard from './pages/AdminDashboard';
import { SiteProvider } from './context/SiteContext';
import { AuthProvider } from './context/AuthContext';
import { Toaster } from './components/ui/toaster';
import { toast } from './hooks/use-toast';
import AuthModal from './components/auth/AuthModal';
import SignupPrompt from './components/auth/SignupPrompt';

function App() {
  useEffect(() => {
    const onNotice = (e) => {
      const d = e.detail || {};
      toast({ title: d.title || 'Notice', description: d.description || '', variant: d.variant });
    };
    window.addEventListener('eg:notice', onNotice);
    return () => window.removeEventListener('eg:notice', onNotice);
  }, []);
  return (
    <div className="App">
      <SiteProvider>
        <AuthProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/admin" element={<AdminLogin />} />
              <Route path="/admin/dashboard" element={<AdminDashboard />} />
            </Routes>
            <AuthModal />
            <SignupPrompt />
          </BrowserRouter>
          <Toaster />
        </AuthProvider>
      </SiteProvider>
    </div>
  );
}

export default App;
