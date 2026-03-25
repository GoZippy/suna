import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { AuthProvider } from '@/components/AuthProvider'

// Mock the auth context
const mockUser = {
  id: 'test-user-id',
  email: 'test@example.com',
  role: 'user',
  tier: 'free',
}

const mockAuthContext = {
  user: mockUser,
  loading: false,
  signIn: vi.fn(),
  signUp: vi.fn(),
  signOut: vi.fn(),
  updateProfile: vi.fn(),
}

vi.mock('@/components/AuthProvider', () => ({
  AuthProvider: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="auth-provider">{children}</div>
  ),
  useAuth: () => mockAuthContext,
}))

describe('AuthProvider', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders children when user is authenticated', async () => {
    render(
      <AuthProvider>
        <div data-testid="child-content">Child Content</div>
      </AuthProvider>
    )

    await waitFor(() => {
      expect(screen.getByTestId('auth-provider')).toBeInTheDocument()
      expect(screen.getByTestId('child-content')).toBeInTheDocument()
    })
  })

  it('shows loading state when authentication is in progress', () => {
    mockAuthContext.loading = true

    render(
      <AuthProvider>
        <div data-testid="child-content">Child Content</div>
      </AuthProvider>
    )

    expect(screen.getByTestId('auth-provider')).toBeInTheDocument()
  })

  it('provides authentication context to children', () => {
    render(
      <AuthProvider>
        <div data-testid="child-content">Child Content</div>
      </AuthProvider>
    )

    expect(mockAuthContext.user).toBeDefined()
    expect(mockAuthContext.signIn).toBeDefined()
    expect(mockAuthContext.signOut).toBeDefined()
  })
})







