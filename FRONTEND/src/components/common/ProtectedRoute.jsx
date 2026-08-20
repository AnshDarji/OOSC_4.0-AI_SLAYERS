import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import PageContainer from './PageContainer';
import LoadingSpinner from './LoadingSpinner';

export default function ProtectedRoute({ children }) {
  const { currentUser, userProfile, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex flex-col items-center justify-center p-6">
        <LoadingSpinner size="lg" />
        <p className="mt-4 text-text-secondary font-medium tracking-tight animate-pulse">Loading secure session...</p>
      </div>
    );
  }

  // User is not authenticated -> redirect to login
  if (!currentUser) {
    return <Navigate to="/login" replace />;
  }



  // Authenticated & synced -> render requested content
  return children;
}
