import React, { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import styles from './AuthGate.module.css';

export interface AuthGateProps {
  onSuccess?: () => void;
}

export const AuthGate: React.FC<AuthGateProps> = ({ onSuccess }) => {
  const {
    signInWithGoogle,
    signInWithEmail,
    signUpWithEmail,
    continueAsGuest,
    isConfigured,
  } = useAuth();

  const [mode, setMode] = useState<'signin' | 'signup'>('signin');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleGoogleSignIn = async () => {
    setError(null);
    setLoading(true);
    try {
      await signInWithGoogle();
      onSuccess?.();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Google sign-in failed.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleEmailSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password.trim()) {
      setError('Please enter both email and password.');
      return;
    }
    setError(null);
    setLoading(true);
    try {
      if (mode === 'signup') {
        await signUpWithEmail(email.trim(), password);
      } else {
        await signInWithEmail(email.trim(), password);
      }
      onSuccess?.();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Authentication failed.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleGuestEntry = () => {
    continueAsGuest();
    onSuccess?.();
  };

  return (
    <div className={styles.gateContainer}>
      <header className={styles.topBar}>
        <span className={styles.wordmark}>TIMESLICEIQ</span>
        <span className={styles.badge}>ACCESS CONTROL // 01</span>
      </header>

      <main id="main-content" tabIndex={-1} className={styles.mainContent}>
        <div className={styles.authCard}>
          <div className={styles.cardHeader}>
            <span className={styles.metaLabel}>AUTHENTICATION REQUIRED</span>
            <h1 className={styles.title}>
              {mode === 'signin' ? 'Sign In to TimeSliceIQ' : 'Create Your Account'}
            </h1>
            <p className={styles.subhead}>
              Sign in to analyze YouTube lectures, query video content with timestamped citations,
              and sync your search history.
            </p>
          </div>

          {!isConfigured && (
            <div className={styles.infoBanner}>
              Firebase credentials are not configured in this environment. You can connect Firebase
              or continue in Guest Mode to explore all features using local browser storage.
            </div>
          )}

          {error && <div className={styles.errorBanner}>{error}</div>}

          {/* 1. Google 1-Click OAuth */}
          <button
            type="button"
            className={styles.googleBtn}
            onClick={handleGoogleSignIn}
            disabled={loading}
          >
            <svg className={styles.googleIcon} viewBox="0 0 24 24" aria-hidden="true">
              <path
                fill="#4285F4"
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              />
              <path
                fill="#34A853"
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              />
              <path
                fill="#FBBC05"
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
              />
              <path
                fill="#EA4335"
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
              />
            </svg>
            Continue with Google
          </button>

          <div className={styles.divider}>
            <div className={styles.dividerLine} />
            <span className={styles.dividerText}>or continue with email</span>
            <div className={styles.dividerLine} />
          </div>

          {/* 2. Email & Password Form */}
          <form className={styles.form} onSubmit={handleEmailSubmit}>
            <div className={styles.fieldGroup}>
              <label className={styles.label} htmlFor="gate-email">
                Email Address
              </label>
              <input
                id="gate-email"
                type="email"
                className={styles.input}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@example.com"
                required
              />
            </div>

            <div className={styles.fieldGroup}>
              <label className={styles.label} htmlFor="gate-password">
                Password
              </label>
              <input
                id="gate-password"
                type="password"
                className={styles.input}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
              />
            </div>

            <button type="submit" className={styles.submitBtn} disabled={loading}>
              {loading ? 'Please wait...' : mode === 'signin' ? 'Sign In' : 'Create Account'}
            </button>
          </form>

          <button
            type="button"
            className={styles.toggleBtn}
            onClick={() => {
              setMode(mode === 'signin' ? 'signup' : 'signin');
              setError(null);
            }}
          >
            {mode === 'signin'
              ? "Don't have an account? Sign up"
              : 'Already have an account? Sign in'}
          </button>

          {/* 3. Guest Entry fallback */}
          <button
            type="button"
            className={styles.guestBtn}
            onClick={handleGuestEntry}
            disabled={loading}
          >
            Continue as Guest (Local Storage)
          </button>
        </div>
      </main>
    </div>
  );
};

export default AuthGate;
