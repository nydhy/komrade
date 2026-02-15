import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import Buddies from '../pages/Buddies'

vi.mock('../api/buddies', () => ({
  getBuddies: vi.fn().mockResolvedValue([]),
}))
vi.mock('../api/auth', () => ({
  getMe: vi.fn().mockResolvedValue({ id: 1, email: 'v@test.com', role: 'veteran', full_name: 'V' }),
}))

describe('Buddies', () => {
  beforeEach(() => {
    localStorage.setItem('vetbridge_token', 'fake-token')
  })

  it('renders Buddies page', async () => {
    render(
      <BrowserRouter>
        <Buddies />
      </BrowserRouter>,
    )
    await screen.findByRole('heading', { name: /my komrades/i })
    expect(screen.getByRole('heading', { name: /komrade links/i })).toBeInTheDocument()
  })
})
