'use client';

import { create } from 'zustand';
import { authService } from '@/lib/api/services/auth';
import { setTokens, clearTokens } from '@/lib/auth';
import type { User } from '@/types';

interface AuthState {
  user: User | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
  checkAuth: () => Promise<void>;
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  isLoading: false,

  login: async (email: string, password: string) => {
    set({ isLoading: true });
    try {
      const response = await authService.login(email, password);
      setTokens(response.access_token, response.refresh_token);
      set({ user: response.user, isLoading: false });
    } catch (error) {
      set({ isLoading: false });
      throw error;
    }
  },

  register: async (email: string, password: string) => {
    set({ isLoading: true });
    try {
      const response = await authService.register(email, password);
      setTokens(response.access_token, response.refresh_token);
      set({ user: response.user, isLoading: false });
    } catch (error) {
      set({ isLoading: false });
      throw error;
    }
  },

  logout: () => {
    clearTokens();
    set({ user: null });
  },

  checkAuth: async () => {
    set({ isLoading: true });
    try {
      const response = await authService.me();
      set({ user: response.user, isLoading: false });
    } catch {
      clearTokens();
      set({ user: null, isLoading: false });
    }
  },
}));
