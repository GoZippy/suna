import { renderHook, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useAgents } from '@/hooks/react-query/agents/use-agents'

// Mock the API call
const mockAgents = [
  {
    id: 'agent-1',
    name: 'Test Agent 1',
    description: 'First test agent',
    created_at: '2024-01-01T00:00:00Z',
    is_active: true,
  },
  {
    id: 'agent-2',
    name: 'Test Agent 2',
    description: 'Second test agent',
    created_at: '2024-01-02T00:00:00Z',
    is_active: false,
  },
]

const mockUseQuery = vi.fn()

vi.mock('@tanstack/react-query', () => ({
  useQuery: (queryKey: any, queryFn: any, options: any) => mockUseQuery(queryKey, queryFn, options),
}))

describe('useAgents', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('returns agents data when query is successful', async () => {
    mockUseQuery.mockReturnValue({
      data: mockAgents,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    })

    const { result } = renderHook(() => useAgents())

    await waitFor(() => {
      expect(result.current.data).toEqual(mockAgents)
      expect(result.current.isLoading).toBe(false)
      expect(result.current.error).toBeNull()
    })
  })

  it('returns loading state when query is in progress', () => {
    mockUseQuery.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
      refetch: vi.fn(),
    })

    const { result } = renderHook(() => useAgents())

    expect(result.current.isLoading).toBe(true)
    expect(result.current.data).toBeUndefined()
  })

  it('returns error when query fails', () => {
    const mockError = new Error('Failed to fetch agents')
    mockUseQuery.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: mockError,
      refetch: vi.fn(),
    })

    const { result } = renderHook(() => useAgents())

    expect(result.current.error).toBe(mockError)
    expect(result.current.isLoading).toBe(false)
  })

  it('calls refetch when refetch function is called', () => {
    const mockRefetch = vi.fn()
    mockUseQuery.mockReturnValue({
      data: mockAgents,
      isLoading: false,
      error: null,
      refetch: mockRefetch,
    })

    const { result } = renderHook(() => useAgents())

    result.current.refetch()
    expect(mockRefetch).toHaveBeenCalled()
  })

  it('passes correct query key to useQuery', () => {
    mockUseQuery.mockReturnValue({
      data: mockAgents,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    })

    renderHook(() => useAgents())

    expect(mockUseQuery).toHaveBeenCalledWith(
      ['agents'],
      expect.any(Function),
      expect.any(Object)
    )
  })
})







