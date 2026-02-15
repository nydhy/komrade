import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
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
  transcribeAudio: vi.fn().mockResolvedValue('voice transcript'),
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

  it('fills message from microphone transcript', async () => {
    const trackStop = vi.fn()
    const mediaStream = {
      getTracks: () => [{ stop: trackStop }],
    } as unknown as MediaStream

    Object.defineProperty(navigator, 'mediaDevices', {
      value: {
        getUserMedia: vi.fn().mockResolvedValue(mediaStream),
      },
      configurable: true,
    })

    class MockMediaRecorder {
      ondataavailable: ((event: BlobEvent) => void) | null = null
      onstop: (() => void) | null = null
      state: RecordingState = 'inactive'

      constructor(_stream: MediaStream) {}

      start() {
        this.state = 'recording'
      }

      stop() {
        this.state = 'inactive'
        this.ondataavailable?.({
          data: new Blob(['audio'], { type: 'audio/webm' }),
        } as BlobEvent)
        this.onstop?.()
      }
    }

    vi.stubGlobal('MediaRecorder', MockMediaRecorder)

    render(
      <BrowserRouter>
        <Translation />
      </BrowserRouter>,
    )

    const startButton = await screen.findByRole('button', { name: /start recording/i })
    fireEvent.click(startButton)

    const stopButton = await screen.findByRole('button', { name: /stop recording/i })
    fireEvent.click(stopButton)

    const textarea = screen.getByPlaceholderText(/type text to translate/i) as HTMLTextAreaElement
    await waitFor(() => expect(textarea.value).toContain('voice transcript'))
    expect(trackStop).toHaveBeenCalled()
  })
})
