import axios from 'axios';

const api = axios.create({
  // VITE_API_BASE_URL is the documented setting. Keep VITE_API_URL as a
  // backwards-compatible alias for existing deployments.
  baseURL: import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor to attach Firebase JWT ID token will be added here in Sprint 1 Phase 2

export default api;
