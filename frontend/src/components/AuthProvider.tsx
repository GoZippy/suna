'use client';

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
} from 'react';

// Mock types for local-only operation
interface LocalUser {
  id: string;
  email: string;
  user_metadata: Record<string, any>;
  app_metadata: Record<string, any>;
  aud: string;
  created_at: string;
}

interface LocalSession {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  token_type: string;
  user: LocalUser;
}

interface LocalAuthClient {
  auth: {
    getSession: () => Promise<{ data: { session: LocalSession | null }; error: null }>;
    signOut: () => Promise<{ error: null }>;
  };
  getSession: () => Promise<LocalSession | null>;
  signOut: () => Promise<void>;
  onAuthStateChange: (callback: (event: string, session: LocalSession | null) => void) => void;
}

type AuthContextType = {
  supabase: LocalAuthClient;
  session: LocalSession | null;
  user: LocalUser | null;
  isLoading: boolean;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [session, setSession] = useState<LocalSession | null>(null);
  const [user, setUser] = useState<LocalUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Mock authentication client for local-only operation
  const supabase: LocalAuthClient = {
    auth: {
      getSession: async () => ({ data: { session }, error: null }),
      signOut: async () => ({ error: null }),
    },
    getSession: async () => session,
    signOut: async () => {
      setSession(null);
      setUser(null);
    },
    onAuthStateChange: (callback) => {
      // Mock auth state change - no real implementation needed
      console.log('Auth state change listener registered (mock)');
    },
  };

  useEffect(() => {
    // Mock authentication for local-only operation
    const mockUser: LocalUser = {
      id: 'local-user',
      email: 'local@localhost',
      user_metadata: {},
      app_metadata: {},
      aud: 'authenticated',
      created_at: new Date().toISOString(),
    };

    const mockSession: LocalSession = {
      access_token: 'mock-token',
      refresh_token: 'mock-refresh',
      expires_in: 3600,
      token_type: 'bearer',
      user: mockUser,
    };

    setSession(mockSession);
    setUser(mockUser);
    setIsLoading(false);
  }, []);

  const signOut = async () => {
    try {
      await supabase.signOut();
    } catch (error) {
      console.error('❌ Error signing out:', error);
    }
  };

  const value = {
    supabase,
    session,
    user,
    isLoading,
    signOut,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
