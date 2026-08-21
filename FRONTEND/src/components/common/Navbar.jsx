import React from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

export default function Navbar({ fullWidth = false }) {
  const { currentUser, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = async () => {
    try {
      await logout();
      navigate('/');
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  const isActive = (path) => location.pathname === path;

  const navLinkStyle = (path) =>
    `text-sm font-medium transition-colors duration-200 ${
      isActive(path)
        ? 'text-text-primary font-semibold'
        : 'text-text-secondary hover:text-text-primary'
    }`;

  return (
    <nav className="fixed top-0 w-full z-50 border-b border-border bg-surface/80 backdrop-blur-xl transition-all">
      <div className={`${fullWidth ? 'w-full' : 'max-w-[1280px]'} mx-auto px-4 md:px-8 flex justify-between items-center h-[72px]`}>
        {/* Logo */}
        <div className="flex items-center gap-12">
          <Link
            to="/"
            className="text-lg font-bold tracking-tight text-text-primary text-[20px] flex items-center gap-2"
          >
            <span className="material-symbols-outlined text-[24px] text-text-primary">gavel</span>
            NYAAY AI
          </Link>

          {/* Navigation Links */}
          <div className="hidden md:flex items-center gap-6">
            <Link to="/" className={navLinkStyle('/')}>
              Home
            </Link>
            {currentUser && (
              <>
                <Link to="/dashboard" className={navLinkStyle('/dashboard')}>
                  Dashboard
                </Link>
                <Link to="/civic" className={navLinkStyle('/civic')}>
                  Civic Navigator
                </Link>
                <Link to="/know-your-kanoon" className={navLinkStyle('/know-your-kanoon')}>
                  Kanoon Q&A
                </Link>
                <Link to="/upload-chat" className={navLinkStyle('/upload-chat')}>
                  Doc Chat
                </Link>
                <Link to="/dochub" className={navLinkStyle('/dochub')}>
                  Legal Drafting
                </Link>
                <Link to="/reasoning" className={navLinkStyle('/reasoning')}>
                  Legal Reasoning
                </Link>
              </>
            )}
          </div>
        </div>

        {/* User / CTA Section */}
        <div className="flex items-center gap-4">
          {currentUser ? (
            <div className="flex items-center gap-4">
              <span className="hidden sm:inline text-xs font-medium text-text-secondary bg-secondary px-3 py-1.5 rounded-button border border-border">
                {currentUser.displayName || currentUser.email}
              </span>
              <button
                onClick={handleLogout}
                className="bg-primary text-white hover:bg-primary-hover px-4 py-2 rounded-button font-medium transition-all text-[13px] shadow-sm"
              >
                Log out
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-3">
              <Link
                to="/login"
                className="text-sm font-medium text-text-secondary hover:text-text-primary transition-colors px-3 py-2"
              >
                Login
              </Link>
              <Link
                to="/signup"
                className="bg-primary text-white hover:bg-primary-hover px-4 py-2 rounded-button font-medium transition-all text-[13px] shadow-sm"
              >
                Sign up
              </Link>
            </div>
          )}
        </div>
      </div>
    </nav>
  );
}
