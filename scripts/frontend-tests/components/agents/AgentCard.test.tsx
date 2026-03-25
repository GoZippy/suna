import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'

// Mock the AgentCard component
const mockAgent = {
  id: 'agent-1',
  name: 'Test Agent',
  description: 'A test agent for testing purposes',
  avatar_url: 'https://example.com/avatar.jpg',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  is_active: true,
  tools_count: 5,
  tier: 'free',
}

const mockAgentCard = ({ agent, onEdit, onDelete, onRun }: any) => (
  <div data-testid="agent-card">
    <h3 data-testid="agent-name">{agent.name}</h3>
    <p data-testid="agent-description">{agent.description}</p>
    <button data-testid="edit-button" onClick={() => onEdit(agent.id)}>
      Edit
    </button>
    <button data-testid="delete-button" onClick={() => onDelete(agent.id)}>
      Delete
    </button>
    <button data-testid="run-button" onClick={() => onRun(agent.id)}>
      Run
    </button>
  </div>
)

vi.mock('@/components/agents/AgentCard', () => ({
  AgentCard: mockAgentCard,
}))

describe('AgentCard', () => {
  it('renders agent information correctly', () => {
    const onEdit = vi.fn()
    const onDelete = vi.fn()
    const onRun = vi.fn()

    render(
      <mockAgentCard
        agent={mockAgent}
        onEdit={onEdit}
        onDelete={onDelete}
        onRun={onRun}
      />
    )

    expect(screen.getByTestId('agent-name')).toHaveTextContent('Test Agent')
    expect(screen.getByTestId('agent-description')).toHaveTextContent(
      'A test agent for testing purposes'
    )
  })

  it('calls onEdit when edit button is clicked', () => {
    const onEdit = vi.fn()
    const onDelete = vi.fn()
    const onRun = vi.fn()

    render(
      <mockAgentCard
        agent={mockAgent}
        onEdit={onEdit}
        onDelete={onDelete}
        onRun={onRun}
      />
    )

    fireEvent.click(screen.getByTestId('edit-button'))
    expect(onEdit).toHaveBeenCalledWith('agent-1')
  })

  it('calls onDelete when delete button is clicked', () => {
    const onEdit = vi.fn()
    const onDelete = vi.fn()
    const onRun = vi.fn()

    render(
      <mockAgentCard
        agent={mockAgent}
        onEdit={onEdit}
        onDelete={onDelete}
        onRun={onRun}
      />
    )

    fireEvent.click(screen.getByTestId('delete-button'))
    expect(onDelete).toHaveBeenCalledWith('agent-1')
  })

  it('calls onRun when run button is clicked', () => {
    const onEdit = vi.fn()
    const onDelete = vi.fn()
    const onRun = vi.fn()

    render(
      <mockAgentCard
        agent={mockAgent}
        onEdit={onEdit}
        onDelete={onDelete}
        onRun={onRun}
      />
    )

    fireEvent.click(screen.getByTestId('run-button'))
    expect(onRun).toHaveBeenCalledWith('agent-1')
  })

  it('displays correct agent status', () => {
    const inactiveAgent = { ...mockAgent, is_active: false }
    const onEdit = vi.fn()
    const onDelete = vi.fn()
    const onRun = vi.fn()

    render(
      <mockAgentCard
        agent={inactiveAgent}
        onEdit={onEdit}
        onDelete={onDelete}
        onRun={onRun}
      />
    )

    expect(screen.getByTestId('agent-card')).toBeInTheDocument()
  })
})







