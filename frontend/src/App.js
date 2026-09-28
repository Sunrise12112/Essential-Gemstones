import React, { useEffect } from 'react';
import './App.css';
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import Home from './pages/Home';
import AdminLogin from './pages/AdminLogin';
import AdminDashboard from './pages/AdminDashboard';
import PaymentSuccess from './pages/PaymentSuccess';
import PaymentCancel from './pages/PaymentCancel';
import { SiteProvider } from './context/SiteContext';
import { AuthProvider } from './context/AuthContext';
import { Toaster } from './components/ui/toaster';
import { toast } from './hooks/use-toast';
import AuthModal from './components/auth/AuthModal';
import AuthCallback from './components/auth/AuthCallback';
import SignupPrompt from './components/auth/SignupPrompt';

// REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
function AppRoutes() {
  const location = useLocation();
  // Synchronously catch the Google OAuth return fragment BEFORE the normal
  // routes run — this avoids race conditions with the AuthProvider's /auth/me check.
  if (location.hash && location.hash.includes('session_id=')) {
    return <AuthCallback />;
  }
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/admin" element={<AdminLogin />} />
      <Route path="/admin/dashboard" element={<AdminDashboard />} />
      <Route path="/payment/success" element={<PaymentSuccess />} />
      <Route path="/payment/cancel" element={<PaymentCancel />} />
    </Routes>
  );
}

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
            <AppRoutes />
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
