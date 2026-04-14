import axios from 'axios';

// Use empty base URL to use relative paths (goes through nginx proxy on same port)
const API_BASE_URL = import.meta.env.VITE_API_URL || '';

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor to handle errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Only handle 401 if we're not already on the login page
    if (error.response?.status === 401 && !window.location.pathname.includes('/login')) {
      console.warn('Unauthorized request - redirecting to login');
      // Token expired or invalid, clear token and redirect to login
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      // Use React Router instead of window.location for cleaner navigation
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  register: (data) => api.post('/api/auth/register', data),
  login: (data) => api.post('/api/auth/login', data),
  getMe: () => api.get('/api/auth/me'),
  logout: () => api.post('/api/auth/logout'),
};

// Users API
export const usersAPI = {
  list: (params) => api.get('/api/users', { params }),
  get: (id) => api.get(`/api/users/${id}`),
  create: (data) => api.post('/api/users', data),
  update: (id, data) => api.put(`/api/users/${id}`, data),
  delete: (id) => api.delete(`/api/users/${id}`),
};

// Clients API
export const clientsAPI = {
  list: (params) => api.get('/api/clients', { params }),
  get: (id) => api.get(`/api/clients/${id}`),
  create: (data) => api.post('/api/clients', data),
  update: (id, data) => api.put(`/api/clients/${id}`, data),
  delete: (id) => api.delete(`/api/clients/${id}`),
};

// POCs API
export const pocsAPI = {
  list: (params) => api.get('/api/pocs', { params }),
  get: (id) => api.get(`/api/pocs/${id}`),
  create: (data) => api.post('/api/pocs', data),
  update: (id, data) => api.put(`/api/pocs/${id}`, data),
  delete: (id) => api.delete(`/api/pocs/${id}`),
};

// Events API
export const eventsAPI = {
  list: (params) => api.get('/api/events', { params }),
  get: (id) => api.get(`/api/events/${id}`),
  create: (data) => api.post('/api/events', data),
  update: (id, data) => api.put(`/api/events/${id}`, data),
  delete: (id) => api.delete(`/api/events/${id}`),
  getMedia: (eventId) => api.get(`/api/events/${eventId}/media`),
  uploadMedia: (eventId, formData) => api.post(`/api/events/${eventId}/media`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
  deleteMedia: (mediaId) => api.delete(`/api/events/media/${mediaId}`),
  downloadMedia: (mediaId) => api.get(`/api/events/media/${mediaId}/download`, {
    responseType: 'blob',
  }),
};

// Intelligence API
export const intelligenceAPI = {
  followUps: {
    list: (params) => api.get('/api/intelligence/follow-ups', { params }),
    get: (id) => api.get(`/api/intelligence/follow-ups/${id}`),
    create: (data) => api.post('/api/intelligence/follow-ups', data),
    update: (id, data) => api.put(`/api/intelligence/follow-ups/${id}`, data),
    delete: (id) => api.delete(`/api/intelligence/follow-ups/${id}`),
  },
  deadlines: {
    list: (params) => api.get('/api/intelligence/deadlines', { params }),
    get: (id) => api.get(`/api/intelligence/deadlines/${id}`),
    create: (data) => api.post('/api/intelligence/deadlines', data),
    update: (id, data) => api.put(`/api/intelligence/deadlines/${id}`, data),
    delete: (id) => api.delete(`/api/intelligence/deadlines/${id}`),
  },
  tasks: {
    list: (params) => api.get('/api/intelligence/tasks', { params }),
    get: (id) => api.get(`/api/intelligence/tasks/${id}`),
    update: (id, data) => api.put(`/api/intelligence/tasks/${id}`, data),
    delete: (id) => api.delete(`/api/intelligence/tasks/${id}`),
  },
};

export default api;
