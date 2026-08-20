import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import Input from '../components/common/Input';
import Button from '../components/common/Button';

export default function Signup() {
  const { signup, signInWithGoogle, error: authError } = useAuth();
  const navigate = useNavigate();

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [validationError, setValidationError] = useState('');

  const validate = () => {
    if (!name.trim()) {
      setValidationError('Name is required.');
      return false;
    }
    if (!email) {
      setValidationError('Email is required.');
      return false;
    }
    if (!/\S+@\S+\.\S+/.test(email)) {
      setValidationError('Please enter a valid email address.');
      return false;
    }
    if (!password) {
      setValidationError('Password is required.');
      return false;
    }
    if (password.length < 6) {
      setValidationError('Password must be at least 6 characters.');
      return false;
    }
    if (password !== confirmPassword) {
      setValidationError('Passwords do not match.');
      return false;
    }
    setValidationError('');
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;

    setLoading(true);
    try {
      await signup(email, password, name);
      // Firebase profile is updated with the name, and the user is authenticated.
      // Redirect to /role-selection immediately.
      navigate('/dashboard');
    } catch (err) {
      console.error('Signup error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleLogin = async () => {
    setLoading(true);
    try {
      await signInWithGoogle();
      navigate('/dashboard');
    } catch (err) {
      console.error('Google login error:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center p-6 text-primary antialiased">
      {/* Back to Home Link */}
      <div className="absolute top-8 left-8">
        <Link
          to="/"
          className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-text-secondary hover:text-primary transition-colors"
        >
          <span className="material-symbols-outlined text-[16px]">arrow_back</span>
          Home
        </Link>
      </div>

      <div className="max-w-md w-full flex flex-col gap-8">
        {/* Brand */}
        <div className="text-center flex flex-col items-center">
          <Link to="/" className="text-2xl font-bold tracking-tighter text-primary flex items-center gap-1.5 mb-2">
            <span className="material-symbols-outlined text-[28px]">gavel</span>
            NYAAY AI
          </Link>
          <p className="text-xs text-text-secondary uppercase font-bold tracking-widest">
            Create Free Account
          </p>
        </div>

        {/* Card containing the form */}
        <div className="bg-background rounded-3xl border border-border p-8 shadow-sm flex flex-col gap-6">
          <h2 className="text-xl font-semibold tracking-tight">Sign Up</h2>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <Input
              label="Full Name"
              id="name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Adv. Priya Sen"
              required
            />
            <Input
              label="Email Address"
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="e.g. counsel@nyaay.ai"
              required
            />
            <Input
              label="Password"
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="•••••••• (Min 6 chars)"
              required
            />
            <Input
              label="Confirm Password"
              id="confirmPassword"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="••••••••"
              required
            />

            {/* Error displays */}
            {(validationError || authError) && (
              <div className="bg-red-500/10 border border-red-500/20 text-red-600 text-xs font-medium rounded-xl p-3 text-left">
                {validationError || authError}
              </div>
            )}

            <Button type="submit" variant="primary" loading={loading} className="w-full mt-2 py-3.5">
              Sign Up with Email
            </Button>
          </form>

          {/* Separator */}
          <div className="flex items-center gap-4 py-1">
            <div className="h-px bg-zinc-200 flex-grow"></div>
            <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">or</span>
            <div className="h-px bg-zinc-200 flex-grow"></div>
          </div>

          {/* Google Sign In */}
          <Button
            type="button"
            variant="outline"
            onClick={handleGoogleLogin}
            disabled={loading}
            className="w-full py-3.5 flex items-center justify-center gap-2"
          >
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" fill="#FBBC05"/>
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" fill="#EA4335"/>
            </svg>
            Sign Up with Google
          </Button>

          {/* Prompt to login */}
          <p className="text-xs text-text-secondary text-center">
            Already have an account?{' '}
            <Link to="/login" className="text-primary font-semibold hover:underline">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
