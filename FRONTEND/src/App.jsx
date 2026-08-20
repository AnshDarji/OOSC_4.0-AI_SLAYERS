import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import ProtectedRoute from './components/common/ProtectedRoute';
import Landing from './pages/Landing';
import Login from './pages/Login';
import Signup from './pages/Signup';
import Dashboard from './pages/Dashboard';
import KnowYourKanoon from './pages/KnowYourKanoon';
import UploadChat from './pages/UploadChat';
import DocHub from './pages/DocHub';
import LegalReasoning from './pages/LegalReasoning';

function App() {
  return (
    <Router>
      <AuthProvider>
        <Routes>
          {/* Public Routes */}
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />

          {/* Protected Routes */}
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/know-your-kanoon"
            element={
              <ProtectedRoute>
                <KnowYourKanoon />
              </ProtectedRoute>
            }
          />
          <Route
            path="/upload-chat"
            element={
              <ProtectedRoute>
                <UploadChat />
              </ProtectedRoute>
            }
          />
          <Route
            path="/dochub"
            element={
              <ProtectedRoute>
                <DocHub />
              </ProtectedRoute>
            }
          />
          <Route
            path="/reasoning"
            element={
              <ProtectedRoute>
                <LegalReasoning />
              </ProtectedRoute>
            }
          />
        </Routes>
      </AuthProvider>
    </Router>
  );
}

export default App;
