import { create } from 'zustand'

interface UserProfile {
  id: number;
  email: string;
  full_name: string;
  is_active: boolean;
  roles: string[];
}

interface AuthState {
  token: string | null;
  user: UserProfile | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (token: string) => void;
  logout: () => void;
  setUser: (user: UserProfile) => void;
  setError: (msg: string | null) => void;
  setLoading: (loading: boolean) => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem('token'),
  user: null,
  isAuthenticated: !!localStorage.getItem('token'),
  isLoading: false,
  error: null,
  
  login: (token: string) => {
    localStorage.setItem('token', token);
    set({ token, isAuthenticated: true, error: null });
  },
  
  logout: () => {
    localStorage.removeItem('token');
    set({ token: null, user: null, isAuthenticated: false, error: null });
  },
  
  setUser: (user: UserProfile) => set({ user }),
  setError: (error: string | null) => set({ error }),
  setLoading: (isLoading: boolean) => set({ isLoading }),
}))
