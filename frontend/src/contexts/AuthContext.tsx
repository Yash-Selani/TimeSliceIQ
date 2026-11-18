/* eslint-disable react-refresh/only-export-components */
import React, { createContext, useContext, useEffect, useState, useMemo } from 'react';
import {
  auth,
  googleProvider,
  isFirebaseConfigured,
} from '../lib/firebase';
import {
  onAuthStateChanged,
  signInWithPopup,
  signInWithRedirect,
  getRedirectResult,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signOut,
  type User,
} from 'firebase/auth';

export interface AuthContextValue {
  user: User | null;
  loading: boolean;
  isConfigured: boolean;
  isGuest: boolean;
  isAuthenticated: boolean;
  continueAsGuest: () => void;
  signInWithGoogle: () => Promise<void>;
  signInWithEmail: (email: string, pass: string) => Promise<void>;
  signUpWithEmail: (email: string, pass: string) => Promise<void>;
  signOutUser: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

const GUEST_KEY = 'timesliceiq_guest_session';

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [isGuest, setIsGuest] = useState<boolean>(() => {
    try {
      return typeof window !== 'undefined' && sessionStorage.getItem(GUEST_KEY) === '1';
    } catch {
      return false;
    }
  });

  useEffect(() => {
    if (!auth || !isFirebaseConfigured) {
      setLoading(false);
      return;
    }

    // Complete any pending Google redirect sign-in gracefully
    getRedirectResult(auth).catch((err) => {
      console.warn('Redirect sign-in check failed:', err);
    });

    const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
      setUser(currentUser);
      if (currentUser) {
        setIsGuest(false);
        try {
          sessionStorage.removeItem(GUEST_KEY);
        } catch {}
      }
      setLoading(false);
    });

    return () => unsubscribe();
  }, []);

  const continueAsGuest = () => {
    setIsGuest(true);
    try {
      sessionStorage.setItem(GUEST_KEY, '1');
    } catch {}
  };

  const signInWithGoogle = async () => {
    if (!auth || !googleProvider) {
      throw new Error('Firebase Authentication is not configured yet. Please provide Firebase keys.');
    }
    try {
      await signInWithPopup(auth, googleProvider);
      setIsGuest(false);
    } catch (err: unknown) {
      const code = (err as { code?: string })?.code || '';
      const msg = err instanceof Error ? err.message : '';
      // If popup is blocked by browser/extensions or unsupported in environment, fall back to redirect
      if (
        code === 'auth/popup-blocked' ||
        code === 'auth/operation-not-supported-in-this-environment' ||
        msg.includes('popup-blocked')
      ) {
        await signInWithRedirect(auth, googleProvider);
        return;
      }
      throw err;
    }
  };

  const signInWithEmail = async (email: string, pass: string) => {
    if (!auth) {
      throw new Error('Firebase Authentication is not configured yet. Please provide Firebase keys.');
    }
    await signInWithEmailAndPassword(auth, email, pass);
    setIsGuest(false);
  };

  const signUpWithEmail = async (email: string, pass: string) => {
    if (!auth) {
      throw new Error('Firebase Authentication is not configured yet. Please provide Firebase keys.');
    }
    await createUserWithEmailAndPassword(auth, email, pass);
    setIsGuest(false);
  };

  const signOutUser = async () => {
    if (auth) {
      await signOut(auth);
    }
    setUser(null);
    setIsGuest(false);
    try {
      sessionStorage.removeItem(GUEST_KEY);
    } catch {}
  };

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      isConfigured: isFirebaseConfigured,
      isGuest,
      isAuthenticated: Boolean(user || isGuest),
      continueAsGuest,
      signInWithGoogle,
      signInWithEmail,
      signUpWithEmail,
      signOutUser,
    }),
    [user, loading, isGuest]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

const defaultAuthValue: AuthContextValue = {
  user: null,
  loading: false,
  isConfigured: false,
  isGuest: false,
  isAuthenticated: false,
  continueAsGuest: () => {},
  signInWithGoogle: async () => {},
  signInWithEmail: async () => {},
  signUpWithEmail: async () => {},
  signOutUser: async () => {},
};

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  return context || defaultAuthValue;
}
