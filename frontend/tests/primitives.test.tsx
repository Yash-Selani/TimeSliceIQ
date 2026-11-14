import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import {
  Button,
  TextInput,
  Chip,
  Tabs,
  Skeleton,
  Rule,
  VisuallyHidden,
} from '../src/components/primitives';

describe('UI Primitives', () => {
  describe('Button', () => {
    it('renders with default primary variant and handles click', () => {
      const handleClick = vi.fn();
      render(<Button onClick={handleClick}>Submit</Button>);
      const button = screen.getByRole('button', { name: 'Submit' });
      expect(button).toBeInTheDocument();
      expect(button).not.toBeDisabled();
      fireEvent.click(button);
      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it('renders ghost and danger variants', () => {
      const { rerender } = render(<Button variant="ghost">Cancel</Button>);
      expect(screen.getByRole('button', { name: 'Cancel' })).toBeInTheDocument();

      rerender(<Button variant="danger">Delete</Button>);
      expect(screen.getByRole('button', { name: 'Delete' })).toBeInTheDocument();
    });

    it('supports sm and md sizes', () => {
      const { rerender } = render(<Button size="sm">Small</Button>);
      expect(screen.getByRole('button', { name: 'Small' })).toBeInTheDocument();

      rerender(<Button size="md">Medium</Button>);
      expect(screen.getByRole('button', { name: 'Medium' })).toBeInTheDocument();
    });

    it('handles disabled state', () => {
      const handleClick = vi.fn();
      render(<Button disabled onClick={handleClick}>Disabled</Button>);
      const button = screen.getByRole('button', { name: 'Disabled' });
      expect(button).toBeDisabled();
      fireEvent.click(button);
      expect(handleClick).not.toHaveBeenCalled();
    });

    it('handles loading state with aria-busy and disables interaction', () => {
      const handleClick = vi.fn();
      render(<Button loading onClick={handleClick}>Processing</Button>);
      const button = screen.getByRole('button', { name: 'Processing' });
      expect(button).toHaveAttribute('aria-busy', 'true');
      expect(button).toBeDisabled();
      fireEvent.click(button);
      expect(handleClick).not.toHaveBeenCalled();
    });
  });

  describe('TextInput', () => {
    it('renders input with label, placeholder, and value', () => {
      const handleChange = vi.fn();
      render(
        <TextInput
          label="Video URL"
          placeholder="https://youtube.com/..."
          value="test"
          onChange={handleChange}
        />,
      );
      expect(screen.getByLabelText('Video URL')).toBeInTheDocument();
      const input = screen.getByPlaceholderText('https://youtube.com/...');
      expect(input).toHaveValue('test');
      fireEvent.change(input, { target: { value: 'test updated' } });
      expect(handleChange).toHaveBeenCalled();
    });

    it('renders error state with aria-invalid and alert', () => {
      render(<TextInput label="Email" error="Invalid URL format" />);
      const input = screen.getByLabelText('Email');
      expect(input).toHaveAttribute('aria-invalid', 'true');
      const errorMsg = screen.getByRole('alert');
      expect(errorMsg).toHaveTextContent('Invalid URL format');
    });

    it('renders textarea when multiline is true', () => {
      render(<TextInput label="Notes" multiline rows={5} />);
      const textarea = screen.getByLabelText('Notes');
      expect(textarea.tagName).toBe('TEXTAREA');
      expect(textarea).toHaveAttribute('rows', '5');
    });

    it('triggers onKeyDown', () => {
      const handleKeyDown = vi.fn();
      render(<TextInput ariaLabel="Search" onKeyDown={handleKeyDown} />);
      const input = screen.getByRole('textbox', { name: 'Search' });
      fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });
      expect(handleKeyDown).toHaveBeenCalled();
    });
  });

  describe('Chip', () => {
    it('renders label and handles click', () => {
      const handleClick = vi.fn();
      render(<Chip label="Summary" onClick={handleClick} />);
      const chip = screen.getByRole('button', { name: 'Summary' });
      expect(chip).toBeInTheDocument();
      fireEvent.click(chip);
      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it('formats seconds prop into MM:SS format when label is omitted', () => {
      render(<Chip seconds={75} />);
      const chip = screen.getByRole('button');
      expect(chip).toHaveTextContent('01:15');
      expect(chip).toHaveAttribute('data-seconds', '75');
    });

    it('formats hours into HH:MM:SS format when seconds >= 3600', () => {
      render(<Chip seconds={3665} />);
      const chip = screen.getByRole('button');
      expect(chip).toHaveTextContent('01:01:05');
    });

    it('reflects active state via aria-pressed', () => {
      render(<Chip label="02:30" active />);
      const chip = screen.getByRole('button', { name: '02:30' });
      expect(chip).toHaveAttribute('aria-pressed', 'true');
    });
  });

  describe('Tabs', () => {
    const tabsData = [
      { id: 'summary', label: 'Summary' },
      { id: 'transcript', label: 'Transcript' },
      { id: 'qa', label: 'Q&A' },
    ];

    it('renders tablist and tabs with correct aria-selected', () => {
      const handleChange = vi.fn();
      render(<Tabs tabs={tabsData} activeId="transcript" onChange={handleChange} />);
      const tablist = screen.getByRole('tablist');
      expect(tablist).toBeInTheDocument();

      const tabs = screen.getAllByRole('tab');
      expect(tabs).toHaveLength(3);
      expect(tabs[1]).toHaveAttribute('aria-selected', 'true');
      expect(tabs[0]).toHaveAttribute('aria-selected', 'false');

      fireEvent.click(tabs[2]);
      expect(handleChange).toHaveBeenCalledWith('qa');
    });

    it('navigates with keyboard arrow keys', () => {
      const handleChange = vi.fn();
      render(<Tabs tabs={tabsData} activeId="summary" onChange={handleChange} />);
      const tabs = screen.getAllByRole('tab');

      tabs[0].focus();
      fireEvent.keyDown(tabs[0], { key: 'ArrowRight' });
      expect(handleChange).toHaveBeenCalledWith('transcript');

      fireEvent.keyDown(tabs[0], { key: 'ArrowLeft' });
      expect(handleChange).toHaveBeenCalledWith('qa');

      fireEvent.keyDown(tabs[0], { key: 'End' });
      expect(handleChange).toHaveBeenCalledWith('qa');

      fireEvent.keyDown(tabs[0], { key: 'Home' });
      expect(handleChange).toHaveBeenCalledWith('summary');
    });
  });

  describe('Skeleton', () => {
    it('renders single skeleton block with aria-hidden="true"', () => {
      const { container } = render(<Skeleton width={200} height={20} />);
      const element = container.querySelector('[aria-hidden="true"]');
      expect(element).toBeInTheDocument();
      expect(element).toHaveStyle({ width: '200px', height: '20px' });
    });

    it('renders multiple lines when lines > 1', () => {
      const { container } = render(<Skeleton lines={3} />);
      const linesContainer = container.querySelector('[aria-hidden="true"]');
      expect(linesContainer).toBeInTheDocument();
      expect(linesContainer?.children).toHaveLength(3);
    });
  });

  describe('Rule', () => {
    it('renders horizontal hairline rule by default', () => {
      render(<Rule spacing="md" />);
      const separator = screen.getByRole('separator');
      expect(separator).toBeInTheDocument();
      expect(separator).toHaveAttribute('aria-orientation', 'horizontal');
    });

    it('renders vertical rule with aria-orientation="vertical"', () => {
      render(<Rule vertical spacing="sm" />);
      const separator = screen.getByRole('separator');
      expect(separator).toHaveAttribute('aria-orientation', 'vertical');
    });
  });

  describe('VisuallyHidden', () => {
    it('renders children with visually-hidden styles', () => {
      render(<VisuallyHidden>Screen reader content</VisuallyHidden>);
      const hidden = screen.getByText('Screen reader content');
      expect(hidden).toBeInTheDocument();
    });

    it('supports custom polymorphic as prop', () => {
      render(<VisuallyHidden as="h2">Hidden Heading</VisuallyHidden>);
      const heading = screen.getByRole('heading', { level: 2 });
      expect(heading).toHaveTextContent('Hidden Heading');
    });
  });
});
