import React, { createContext, useContext, useState, useEffect } from 'react';
import { 
  signInWithEmailAndPassword, 
  createUserWithEmailAndPassword, 
  signOut, 
  signInWithPopup, 
  GoogleAuthProvider,
  updateProfile,
  onAuthStateChanged 
} from 'firebase/auth';
import { auth } from '../config/firebase';
import authService from '../services/authService';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [currentUser, setCurrentUser] = useState(null);
  const [userProfile, setUserProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fallback simulator state if Firebase auth is null (mock-api-key)
  const [mockUser, setMockUser] = useState(null);

  // Load profile from backend when Firebase user is available
  const fetchProfile = async (fbUser) => {
    try {
      const token = fbUser.uid === 'mock-uid' ? 'mock-token' : await fbUser.getIdToken();
      const profile = await authService.fetchCurrentUser(token);
      setUserProfile(profile);
      setError(null);
    } catch (err) {
      if (err.response && err.response.status === 404) {
        try {
          const token = fbUser.uid === 'mock-uid' ? 'mock-token' : await fbUser.getIdToken();
          const profile = await authService.syncUserProfile(token, fbUser.displayName || fbUser.email, 'CITIZEN');
          setUserProfile(profile);
          setError(null);
        } catch (syncErr) {
          console.error("Failed to auto-sync profile", syncErr);
        }
      } else {
        console.error('Error fetching backend user profile:', err);
        setError('Failed to sync profile with database.');
      }
    }
  };

  useEffect(() => {
    if (auth) {
      const unsubscribe = onAuthStateChanged(auth, async (user) => {
        setCurrentUser(user);
        if (user) {
          await fetchProfile(user);
        } else {
          setUserProfile(null);
        }
        setLoading(false);
      });
      return unsubscribe;
    } else {
      // Setup mock auth listener for dev-only if keys are missing
      console.warn('Firebase auth client not initialized. Operating in local simulator mode.');
      if (mockUser) {
        fetchProfile(mockUser).then(() => setLoading(false));
      } else {
        setUserProfile(null);
        setLoading(false);
      }
    }
  }, [mockUser]);

  // Auth Operations
  const signup = async (email, password, name) => {
    setError(null);
    setLoading(true);
    if (auth) {
      try {
        const userCredential = await createUserWithEmailAndPassword(auth, email, password);
        await updateProfile(userCredential.user, { displayName: name });
        // The onAuthStateChanged observer will trigger fetchProfile
        return userCredential.user;
      } catch (err) {
        setError(err.message);
        setLoading(false);
        throw err;
      }
    } else {
      // Mock signup
      const newUser = { uid: 'mock-uid', email, displayName: name, getIdToken: () => 'mock-token' };
      setMockUser(newUser);
      setCurrentUser(newUser);
      return newUser;
    }
  };

  const login = async (email, password) => {
    setError(null);
    setLoading(true);
    if (auth) {
      try {
        const userCredential = await signInWithEmailAndPassword(auth, email, password);
        return userCredential.user;
      } catch (err) {
        setError(err.message);
        setLoading(false);
        throw err;
      }
    } else {
      // Mock login
      const loggedUser = { uid: 'mock-uid', email, displayName: 'Mock User', getIdToken: () => 'mock-token' };
      setMockUser(loggedUser);
      setCurrentUser(loggedUser);
      return loggedUser;
    }
  };

  const logout = async () => {
    setError(null);
    setLoading(true);
    if (auth) {
      try {
        await signOut(auth);
        setCurrentUser(null);
        setUserProfile(null);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    } else {
      setMockUser(null);
      setCurrentUser(null);
      setUserProfile(null);
      setLoading(false);
    }
  };

  const signInWithGoogle = async () => {
    setError(null);
    setLoading(true);
    if (auth) {
      try {
        const provider = new GoogleAuthProvider();
        const result = await signInWithPopup(auth, provider);
        return result.user;
      } catch (err) {
        setError(err.message);
        setLoading(false);
        throw err;
      }
    } else {
      // Mock Google Login
      const googleUser = { uid: 'mock-uid', email: 'google-user@nyaay.ai', displayName: 'Google User', getIdToken: () => 'mock-token' };
      setMockUser(googleUser);
      setCurrentUser(googleUser);
      return googleUser;
    }
  };

  const syncProfile = async (role) => {
    if (!currentUser) throw new Error('No authenticated user found');
    setError(null);
    try {
      const token = currentUser.uid === 'mock-uid' ? 'mock-token' : await currentUser.getIdToken();
      const profile = await authService.syncUserProfile(token, currentUser.displayName || currentUser.email, role);
      setUserProfile(profile);
      return profile;
    } catch (err) {
      setError('Database synchronization failed.');
      throw err;
    }
  };

  const value = {
    currentUser,
    userProfile,
    loading,
    error,
    signup,
    login,
    logout,
    signInWithGoogle,
    syncProfile,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
