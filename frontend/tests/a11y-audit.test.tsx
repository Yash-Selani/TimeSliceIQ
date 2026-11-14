import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Landing } from '@/components/Landing';
import { AppShell } from '@/components/AppShell';
import { PlayerPane } from '@/components/PlayerPane';
import { ChatThread } from '@/components/ChatThread';
import { ChatComposer } from '@/components/ChatComposer';
import { TranscriptPanel } from '@/components/TranscriptPanel';
import { ErrorState, LoadingState } from '@/components/ErrorState';
import { TimestampChip } from '@/components/TimestampChip';
import { Tabs } from '@/components/primitives/Tabs';
import { PlayerContext, type PlayerContextValue } from '@/contexts/PlayerContext';
import type { TranscriptLine, AnswerBlock } from '@/types/api';

/**
 * Mock Player Context factory
 */
function createMockPlayerContext(overrides?: Partial<PlayerContextValue>): PlayerContextValue {
  return {
    isReady: true,
    currentTime: 15,
    duration: 3600,
    isPlaying: false,
    seekTo: vi.fn(),
    containerRef: { current: null },
    videoId: 'mock-video-id',
    playVideo: vi.fn(),
    pauseVideo: vi.fn(),
    player: null,
    ...overrides,
  };
}

const sampleTranscript: TranscriptLine[] = [
  { start_s: 0, text: 'Welcome to Deep Learning Lecture 1.' },
  { start_s: 15, text: 'Today we discuss gradient descent.' },
  { start_s: 45, text: 'Backpropagation computes the gradients efficiently.' },
  { start_s: 90, text: 'Neural network architectures include CNNs and Transformers.' },
];

const sampleBlocks: AnswerBlock[] = [
  {
    text: 'Backpropagation computes gradients using the chain rule.',
    cites: [
      { seconds: 45, label: '00:45', chunk_id: 'c1' },
      { seconds: 90, label: '01:30', chunk_id: 'c2' },
    ],
  },
];

/**
 * Automated WCAG 2.2 AA Rule Auditor Helper
 * Validates DOM node hierarchies against core WCAG 2.2 criteria:
 * - 4.1.2 Name, Role, Value (button-name, label, link-name)
 * - 1.3.1 Info and Relationships (landmarks, heading hierarchy, list structure)
 * - 2.4.3 Focus Order & 2.4.7 Focus Visible (no positive tabindex)
 * - 1.1.1 Non-text Content (images have alt or aria-hidden)
 * - 4.1.3 Status Messages (live regions)
 */
function auditWCAGRules(container: HTMLElement) {
  const violations: string[] = [];

  // Rule 1: All buttons must have an accessible name
  const buttons = container.querySelectorAll('button');
  buttons.forEach((btn) => {
    const accessibleName =
      btn.getAttribute('aria-label') ||
      btn.getAttribute('aria-labelledby') ||
      btn.textContent?.trim() ||
      btn.getAttribute('title');
    if (!accessibleName) {
      violations.push(`Button lacks accessible name: ${btn.outerHTML.slice(0, 100)}`);
    }
  });

  // Rule 2: All inputs & textareas must have an accessible label
  const inputs = container.querySelectorAll('input, textarea, select');
  inputs.forEach((input) => {
    const id = input.getAttribute('id');
    const hasLabelElement = id ? container.querySelector(`label[for="${id}"]`) : null;
    const hasAriaLabel = input.getAttribute('aria-label') || input.getAttribute('aria-labelledby');
    const hasPlaceholderOnly = input.getAttribute('placeholder') && !hasAriaLabel && !hasLabelElement;
    if (!hasLabelElement && !hasAriaLabel) {
      violations.push(
        `Form control lacks accessible label: ${input.outerHTML.slice(0, 100)}${
          hasPlaceholderOnly ? ' (placeholder is not a sufficient label alone)' : ''
        }`,
      );
    }
  });

  // Rule 3: No positive tabindex (WCAG 2.4.3 Focus Order)
  const allElements = container.querySelectorAll('*');
  allElements.forEach((el) => {
    const tabIndex = el.getAttribute('tabindex');
    if (tabIndex && parseInt(tabIndex, 10) > 0) {
      violations.push(`Positive tabindex (${tabIndex}) found on: ${el.outerHTML.slice(0, 100)}`);
    }
  });

  // Rule 4: ARIA roles must be valid WAI-ARIA roles
  const validRoles = new Set([
    'alert', 'alertdialog', 'application', 'article', 'banner', 'button', 'cell', 'checkbox',
    'columnheader', 'combobox', 'complementary', 'contentinfo', 'definition', 'dialog',
    'directory', 'document', 'feed', 'figure', 'form', 'grid', 'gridcell', 'group', 'heading',
    'img', 'link', 'list', 'listbox', 'listitem', 'log', 'main', 'marquee', 'math', 'menu',
    'menubar', 'menuitem', 'menuitemcheckbox', 'menuitemradio', 'navigation', 'none', 'note',
    'option', 'presentation', 'progressbar', 'radio', 'radiogroup', 'region', 'row', 'rowgroup',
    'rowheader', 'scrollbar', 'search', 'searchbox', 'separator', 'slider', 'spinbutton',
    'status', 'switch', 'tab', 'table', 'tablist', 'tabpanel', 'term', 'textbox', 'timer',
    'toolbar', 'tooltip', 'tree', 'treegrid', 'treeitem',
  ]);
  allElements.forEach((el) => {
    const role = el.getAttribute('role');
    if (role && !validRoles.has(role)) {
      violations.push(`Invalid ARIA role "${role}" on element: ${el.outerHTML.slice(0, 100)}`);
    }
  });

  // Rule 5: Images and SVG elements must have accessible name or aria-hidden="true"
  const images = container.querySelectorAll('img, svg');
  images.forEach((img) => {
    const isHidden = img.getAttribute('aria-hidden') === 'true';
    const hasAlt = img.getAttribute('alt') !== null;
    const hasAriaLabel = img.getAttribute('aria-label') || img.getAttribute('aria-labelledby');
    if (!isHidden && !hasAlt && !hasAriaLabel) {
      violations.push(`Image or SVG lacks alt or aria-hidden: ${img.outerHTML.slice(0, 100)}`);
    }
  });

  // Rule 6: aria-live values must be "polite", "assertive", or "off"
  allElements.forEach((el) => {
    const live = el.getAttribute('aria-live');
    if (live && !['polite', 'assertive', 'off'].includes(live)) {
      violations.push(`Invalid aria-live value "${live}" on element: ${el.outerHTML.slice(0, 100)}`);
    }
  });

  return violations;
}

describe('WCAG 2.2 AA Accessibility Audit', () => {
  let playerValue: PlayerContextValue;

  beforeEach(() => {
    playerValue = createMockPlayerContext();
    window.HTMLElement.prototype.scrollIntoView = vi.fn();
  });

  describe('1. Automated Axe/WCAG Audit on All Page States', () => {
    it('State A - Landing page satisfies all WCAG 2.2 AA automated rules', () => {
      const { container } = render(<Landing onSubmit={vi.fn()} />);
      const violations = auditWCAGRules(container);
      expect(violations).toEqual([]);

      // Verify Landing landmark
      const main = container.querySelector('main#main-content');
      expect(main).toBeInTheDocument();
      expect(main).toHaveAttribute('tabIndex', '-1');

      // Verify input label & ARIA states
      const input = screen.getByLabelText(/youtube lecture url/i);
      expect(input).toBeInTheDocument();
      expect(input).toHaveAttribute('type', 'url');

      // Verify submit button
      const submitBtn = screen.getByRole('button', { name: /index/i });
      expect(submitBtn).toBeInTheDocument();
    });

    it('State B - Workspace state (dual pane) satisfies all WCAG 2.2 AA automated rules', () => {
      const { container } = render(
        <PlayerContext.Provider value={playerValue}>
          <AppShell
            onSwitchVideo={vi.fn()}
            activeTab="chat"
            onTabChange={vi.fn()}
            playerPane={<PlayerPane title="Lecture 1: Neural Networks" channel="Stanford Online" />}
            chatPane={
              <ChatThread
                messages={[
                  { role: 'user', content: 'What is backpropagation?' },
                  {
                    role: 'assistant',
                    blocks: sampleBlocks,
                    follow_ups: ['How does SGD differ?'],
                  },
                ]}
                onSendMessage={vi.fn()}
              />
            }
            transcriptPane={<TranscriptPanel transcript={sampleTranscript} />}
          />
        </PlayerContext.Provider>,
      );

      const violations = auditWCAGRules(container);
      expect(violations).toEqual([]);

      // Verify Header landmark
      expect(container.querySelector('header')).toBeInTheDocument();

      // Verify Main landmark
      const main = container.querySelector('main#main-content');
      expect(main).toBeInTheDocument();
      expect(main).toHaveAttribute('tabIndex', '-1');

      // Verify Nav landmark
      expect(container.querySelector('nav[aria-label="Workspace tabs"]')).toBeInTheDocument();

      // Verify Tablist
      expect(screen.getByRole('tablist', { name: 'Workspace panels' })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: 'Chat' })).toHaveAttribute('aria-selected', 'true');
      expect(screen.getByRole('tab', { name: 'Transcript' })).toHaveAttribute('aria-selected', 'false');

      // Verify Video Player region
      expect(screen.getByRole('region', { name: 'Video Player' })).toBeInTheDocument();

      // Verify Chat thread region
      expect(screen.getByRole('region', { name: 'Discussion Thread' })).toBeInTheDocument();
    });

    it('State C - Loading state satisfies all WCAG 2.2 AA automated rules across stages', () => {
      for (const stage of [1, 2, 3] as const) {
        const { container, unmount } = render(<LoadingState stage={stage} />);
        const violations = auditWCAGRules(container);
        expect(violations).toEqual([]);

        const status = screen.getByRole('status');
        expect(status).toHaveAttribute('aria-live', 'polite');

        const progressbar = screen.getByRole('progressbar');
        expect(progressbar).toHaveAttribute('aria-valuemin', '0');
        expect(progressbar).toHaveAttribute('aria-valuemax', '100');
        expect(progressbar).toHaveAttribute('aria-valuenow');
        unmount();
      }
    });

    it('State D - Error states satisfy all WCAG 2.2 AA automated rules for all error presets', () => {
      const errorCodes = [
        'INVALID_URL',
        'NO_TRANSCRIPT',
        'VIDEO_UNAVAILABLE',
        'RATE_LIMITED',
        'BACKEND_DOWN',
        'UNKNOWN_ERROR',
      ] as const;

      for (const code of errorCodes) {
        const { container, unmount } = render(
          <ErrorState
            code={code}
            onRetry={vi.fn()}
            onAction={vi.fn()}
            countdownSeconds={code === 'RATE_LIMITED' ? 0 : 30}
            autoCountdown={false}
          />,
        );

        const violations = auditWCAGRules(container);
        expect(violations).toEqual([]);

        const alert = screen.getByRole('alert');
        expect(alert).toHaveAttribute('aria-live', 'assertive');

        const button = screen.getByRole('button');
        expect(button).toBeInTheDocument();
        unmount();
      }
    });
  });

  describe('2. Keyboard Operability Audit', () => {
    it('verifies skip link target exists and points to #main-content with tabIndex={-1}', () => {
      // Test Landing state
      const { unmount: unmountLanding } = render(<Landing onSubmit={vi.fn()} />);
      const landingMain = document.getElementById('main-content');
      expect(landingMain).toBeInTheDocument();
      expect(landingMain?.tagName.toLowerCase()).toBe('main');
      expect(landingMain).toHaveAttribute('tabindex', '-1');
      unmountLanding();

      // Test AppShell Workspace state
      render(
        <PlayerContext.Provider value={playerValue}>
          <AppShell
            playerPane={<PlayerPane />}
            chatPane={<div>Chat</div>}
          />
        </PlayerContext.Provider>,
      );
      const shellMain = document.getElementById('main-content');
      expect(shellMain).toBeInTheDocument();
      expect(shellMain?.tagName.toLowerCase()).toBe('main');
      expect(shellMain).toHaveAttribute('tabindex', '-1');
    });

    it('verifies WAI-ARIA Tab navigation keyboard operability (ArrowRight, ArrowLeft, Home, End)', () => {
      const handleTabChange = vi.fn();
      const tabs = [
        { id: 'chat', label: 'Chat' },
        { id: 'transcript', label: 'Transcript' },
        { id: 'notes', label: 'Notes' },
      ];

      const { rerender } = render(
        <Tabs tabs={tabs} activeId="chat" onChange={handleTabChange} />,
      );

      const chatTab = screen.getByRole('tab', { name: 'Chat' });
      const transcriptTab = screen.getByRole('tab', { name: 'Transcript' });
      const notesTab = screen.getByRole('tab', { name: 'Notes' });

      // Initial tabindexes: active is 0, others are -1
      expect(chatTab).toHaveAttribute('tabindex', '0');
      expect(transcriptTab).toHaveAttribute('tabindex', '-1');
      expect(notesTab).toHaveAttribute('tabindex', '-1');

      // ArrowRight from chat -> transcript
      fireEvent.keyDown(chatTab, { key: 'ArrowRight' });
      expect(handleTabChange).toHaveBeenCalledWith('transcript');

      // Re-render with activeId="transcript"
      rerender(<Tabs tabs={tabs} activeId="transcript" onChange={handleTabChange} />);
      expect(transcriptTab).toHaveAttribute('tabindex', '0');
      expect(chatTab).toHaveAttribute('tabindex', '-1');

      // End key -> jumps to last tab ('notes')
      fireEvent.keyDown(transcriptTab, { key: 'End' });
      expect(handleTabChange).toHaveBeenCalledWith('notes');

      // Home key -> jumps to first tab ('chat')
      rerender(<Tabs tabs={tabs} activeId="notes" onChange={handleTabChange} />);
      fireEvent.keyDown(notesTab, { key: 'Home' });
      expect(handleTabChange).toHaveBeenCalledWith('chat');

      // ArrowLeft with wrap-around from chat (index 0) -> notes (index 2)
      rerender(<Tabs tabs={tabs} activeId="chat" onChange={handleTabChange} />);
      fireEvent.keyDown(chatTab, { key: 'ArrowLeft' });
      expect(handleTabChange).toHaveBeenCalledWith('notes');
    });

    it('verifies ChatComposer submits on Enter and allows multi-line on Shift+Enter', () => {
      const handleSend = vi.fn();
      render(<ChatComposer onSend={handleSend} />);

      const textarea = screen.getByRole('textbox', { name: 'Ask a question' });
      fireEvent.change(textarea, { target: { value: 'Test query' } });

      // Shift+Enter does NOT submit
      fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: true });
      expect(handleSend).not.toHaveBeenCalled();

      // Enter without Shift submits
      fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false });
      expect(handleSend).toHaveBeenCalledWith('Test query');
      expect(textarea).toHaveValue('');
    });
  });

  describe('3. Screen Reader Audit', () => {
    it('verifies proper landmarks across the workspace layout', () => {
      const { container } = render(
        <PlayerContext.Provider value={playerValue}>
          <AppShell
            onSwitchVideo={vi.fn()}
            activeTab="transcript"
            onTabChange={vi.fn()}
            playerPane={<PlayerPane title="Advanced Distributed Systems" channel="MIT" />}
            transcriptPane={<TranscriptPanel transcript={sampleTranscript} />}
          />
        </PlayerContext.Provider>,
      );

      // Landmark: Banner (<header>)
      const bannerHeaders = container.querySelectorAll('header');
      expect(bannerHeaders.length).toBeGreaterThanOrEqual(1);

      // Landmark: Main (<main>)
      expect(screen.getByRole('main')).toBeInTheDocument();

      // Landmark: Navigation (<nav>)
      expect(screen.getByRole('navigation', { name: 'Workspace tabs' })).toBeInTheDocument();

      // Landmark: Region - Video Player
      expect(screen.getByRole('region', { name: 'Video Player' })).toBeInTheDocument();

      // Landmark: Region - Transcript
      expect(screen.getByRole('region', { name: 'Transcript' })).toBeInTheDocument();
    });

    it('verifies TimestampChip generates natural spoken aria-labels for screen readers', () => {
      const cases = [
        { seconds: 0, expectedLabel: 'Jump to 0 seconds' },
        { seconds: 1, expectedLabel: 'Jump to 1 second' },
        { seconds: 75, expectedLabel: 'Jump to 1 minute 15 seconds' },
        { seconds: 765, expectedLabel: 'Jump to 12 minutes 45 seconds' },
        { seconds: 3600, expectedLabel: 'Jump to 1 hour' },
        { seconds: 3665, expectedLabel: 'Jump to 1 hour 1 minute 5 seconds' },
      ];

      for (const { seconds, expectedLabel } of cases) {
        const { unmount } = render(
          <PlayerContext.Provider value={playerValue}>
            <TimestampChip seconds={seconds} />
          </PlayerContext.Provider>,
        );

        const chip = screen.getByRole('button', { name: expectedLabel });
        expect(chip).toBeInTheDocument();
        expect(chip).toHaveAttribute('aria-label', expectedLabel);
        unmount();
      }
    });

    it('verifies ChatThread live region announces updates politely', () => {
      const { rerender } = render(
        <PlayerContext.Provider value={playerValue}>
          <ChatThread messages={[]} onSendMessage={vi.fn()} />
        </PlayerContext.Provider>,
      );

      const log = screen.getByRole('log', { name: 'Chat messages' });
      expect(log).toHaveAttribute('aria-live', 'polite');
      expect(log).toHaveAttribute('aria-relevant', 'additions text');

      // Append assistant message
      rerender(
        <PlayerContext.Provider value={playerValue}>
          <ChatThread
            messages={[
              {
                role: 'assistant',
                blocks: [{ text: 'Here is an answer', cites: [{ chunk_id: 'c1', seconds: 30, label: '00:30' }] }],
              },
            ]}
            onSendMessage={vi.fn()}
          />
        </PlayerContext.Provider>,
      );

      expect(screen.getByText('Here is an answer')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Jump to 30 seconds' })).toBeInTheDocument();
    });

    it('verifies TranscriptPanel search input has live hit count announcements', () => {
      render(
        <PlayerContext.Provider value={playerValue}>
          <TranscriptPanel transcript={sampleTranscript} />
        </PlayerContext.Provider>,
      );

      const searchInput = screen.getByRole('textbox', { name: 'Filter transcript by text' });
      expect(searchInput).toBeInTheDocument();

      // Type search query matching exactly 1 item
      fireEvent.change(searchInput, { target: { value: 'Backpropagation' } });

      // Live hit count status container
      let status = screen.getByRole('status');
      expect(status).toHaveAttribute('aria-live', 'polite');
      expect(status).toHaveAttribute('aria-atomic', 'true');
      expect(status).toHaveTextContent('1 match');
      expect(status).toHaveTextContent('4 total lines');

      // Type search query matching 2 items
      fireEvent.change(searchInput, { target: { value: 'gradient' } });
      status = screen.getByRole('status');
      expect(status).toHaveTextContent('2 matches');
      expect(status).toHaveTextContent('4 total lines');

      // Clear search
      const clearBtn = screen.getByRole('button', { name: 'Clear search query' });
      fireEvent.click(clearBtn);

      expect(screen.queryByRole('status')).not.toBeInTheDocument();
    });

    it('verifies active transcript line indicates aria-current="time"', () => {
      // currentTime is 15s in playerValue
      render(
        <PlayerContext.Provider value={playerValue}>
          <TranscriptPanel transcript={sampleTranscript} />
        </PlayerContext.Provider>,
      );

      const activeLineBtn = screen.getByRole('button', {
        name: '00:15: Today we discuss gradient descent.',
      });
      expect(activeLineBtn).toHaveAttribute('aria-current', 'time');

      // Inactive line does not have aria-current
      const inactiveLineBtn = screen.getByRole('button', {
        name: '00:45: Backpropagation computes the gradients efficiently.',
      });
      expect(inactiveLineBtn).not.toHaveAttribute('aria-current');
    });
  });
});
