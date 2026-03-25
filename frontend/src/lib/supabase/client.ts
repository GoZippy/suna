// Mock Supabase client for local-only operation
import { jwtDecode } from 'jwt-decode'

export interface LocalUser {
  id: string
  email: string
  role: string
  tier: string
  created_at: string
  updated_at: string
  user_metadata: Record<string, any>
  app_metadata: Record<string, any>
  aud: string
}

export interface LocalSession {
  access_token: string
  refresh_token: string
  user: LocalUser
  expires_at: number
}

export class LocalAuthClient {
  private session: LocalSession | null = null
  private listeners: Array<(event: string, session: LocalSession | null) => void> = []

  constructor() {
    // Create a mock session for local-only operation
    this.createMockSession()
  }

  private createMockSession() {
    const mockUser: LocalUser = {
      id: 'local-user',
      email: 'local@localhost',
      role: 'user',
      tier: 'local',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      user_metadata: {},
      app_metadata: {},
      aud: 'authenticated',
    }

    this.session = {
      access_token: 'mock-access-token',
      refresh_token: 'mock-refresh-token',
      user: mockUser,
      expires_at: Date.now() + 3600000, // 1 hour from now
    }
  }

  async getSession(): Promise<LocalSession | null> {
    return this.session
  }

  async signOut(): Promise<void> {
    this.session = null
    // Notify listeners
    this.listeners.forEach(listener => listener('SIGNED_OUT', null))
  }

  onAuthStateChange(callback: (event: string, session: LocalSession | null) => void): void {
    this.listeners.push(callback)
    // Immediately call with current session
    callback('SIGNED_IN', this.session)
  }

  // Mock auth methods
  auth = {
    getSession: async () => ({ data: { session: this.session }, error: null }),
    getUser: async () => ({ data: { user: this.session?.user }, error: null }),
    signOut: async () => ({ error: null }),
    signInWithPassword: async () => ({ data: { session: this.session }, error: null }),
    signUp: async () => ({ data: { session: this.session }, error: null }),
    signInWithOAuth: async (options: any) => ({ data: { session: this.session }, error: null }),
    onAuthStateChange: (callback: (event: string, session: LocalSession | null) => void) => {
      const subscription = {
        data: { subscription: { unsubscribe: () => {} } }
      }
      // Immediately call with current session
      callback('SIGNED_IN', this.session)
      return subscription
    },
  }

  // Mock storage methods
  storage = {
    from: (bucket: string) => ({
      upload: async () => ({ data: { path: 'mock-path' }, error: null }),
      download: async () => ({ data: new Blob(), error: null }),
      remove: async () => ({ data: null, error: null }),
      list: async () => ({ data: [], error: null }),
    }),
  }

  // Mock database methods
  from = (table: string) => ({
    select: (columns?: string) => ({
      eq: (column: string, value: any) => ({
        single: async () => ({ data: null, error: null }),
        execute: async () => ({ data: [], error: null }),
      }),
      execute: async () => ({ data: [], error: null }),
    }),
    insert: async (data: any) => ({ data: null, error: null }),
    update: (data: any) => ({
      eq: (column: string, value: any) => ({
        select: (columns?: string) => ({
          single: async () => ({ data: null, error: null }),
        }),
      }),
    }),
    delete: () => ({
      eq: (column: string, value: any) => ({ data: null, error: null }),
    }),
  })

  // Mock RPC methods
  rpc = async (func: string, params?: any) => ({ data: null, error: null })

  // Mock realtime methods
  channel = (name: string) => ({
    on: () => this,
    subscribe: () => this,
    unsubscribe: () => this,
  })
}

// Export a default instance
export const createClient = () => new LocalAuthClient()
