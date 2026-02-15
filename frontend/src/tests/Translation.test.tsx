import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import Translation from '../pages/Translation'

vi.mock('../api/translate', () => ({
  getTranslateHistory: vi.fn().mockResolvedValue([
    {
      created_at: '2026-01-01T00:00:00Z',
      user_id: 1,
      question: 'history question',
      response: 'history response',
      context: null,
      empathetic_personalized_answer: 'history response',
      safety_flag: 'normal',
    },
  ]),
  translateText: vi.fn().mockResolvedValue({
    empathetic_personalized_answer: 'empathetic output',
    safety_flag: 'normal',
  }),
}))

describe('Translation page', () => {
  it('renders translation page and history', async () => {
    render(
      <BrowserRouter>
        <Translation />
      </BrowserRouter>,
    )

    await screen.findByRole('heading', { name: /chat with komradeai/i })
    expect(await screen.findByText(/history question/i)).toBeInTheDocument()
  })

  it('loads outputs when clicking a history item', async () => {
    render(
      <BrowserRouter>
        <Translation />
      </BrowserRouter>,
    )

    const historyButton = await screen.findByRole('button', { name: /history question/i })
    fireEvent.click(historyButton)

    const matches = await screen.findAllByText(/history response/i)
    expect(matches.length).toBeGreaterThan(0)
  })
})
