import React, { createContext, useContext, useState, useEffect } from 'react';
import { User } from '../types';
import { authService } from '../services/api';

interface AuthContextType {
  user: User | null;
  login: (identifier: string, pwd: string) => Promise<User>;
  signup: (name: string, username: string, email: string, pwd: string) => Promise<User>;
  googleAuth: (payload: { code?: string; email?: string; name?: string; google_id?: string }) => Promise<User>;
  logout: () => void;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(() => {
    const saved = localStorage.getItem('career_twin_user');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch (e) {
        return null;
      }
    }
    return null;
  });
  const [isLoading, setIsLoading] = useState(false);

  const login = async (identifier: string, pwd: string): Promise<User> => {
    setIsLoading(true);
    try {
      const u = await authService.login(identifier, pwd);
      setUser(u);
      localStorage.setItem('career_twin_user', JSON.stringify(u));
      return u;
    } finally {
      setIsLoading(false);
    }
  };

  const signup = async (name: string, username: string, email: string, pwd: string): Promise<User> => {
    setIsLoading(true);
    try {
      const u = await authService.signup(name, username, email, pwd);
      setUser(u);
      localStorage.setItem('career_twin_user', JSON.stringify(u));
      return u;
    } finally {
      setIsLoading(false);
    }
  };

  const googleAuth = async (payload: { code?: string; email?: string; name?: string; google_id?: string }): Promise<User> => {
    setIsLoading(true);
    try {
      const u = await authService.googleAuth(payload);
      setUser(u);
      localStorage.setItem('career_twin_user', JSON.stringify(u));
      return u;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem('career_twin_user');
  };

  return (
    <AuthContext.Provider value={{ user, login, signup, googleAuth, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

