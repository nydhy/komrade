import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import Translation from '../pages/Translation'

vi.mock('../api/translate', () => ({
  getTranslateHistory: vi.fn().mockResolvedValue([
    {
      created_at: '2026-01-01T00:00:00Z',
      user_id: 1,
      provider: 'ollama',
      message: 'history item',
      context: null,
      generic_answer: 'history generic',
      empathetic_personalized_answer: 'history empathetic',
      safety_flag: 'normal',
    },
  ]),
  translateText: vi.fn().mockResolvedValue({
    generic_answer: 'generic output',
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

    await screen.findByRole('heading', { name: /translation layer/i })
    expect(await screen.findByText(/history item/i)).toBeInTheDocument()
  })

  it('loads outputs when clicking a history item', async () => {
    render(
      <BrowserRouter>
        <Translation />
      </BrowserRouter>,
    )

    const historyButton = await screen.findByRole('button', { name: /history item/i })
    fireEvent.click(historyButton)

    expect(await screen.findByText(/history generic/i)).toBeInTheDocument()
    expect(await screen.findByText(/history empathetic/i)).toBeInTheDocument()
  })
})
