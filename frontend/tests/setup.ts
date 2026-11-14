import '@testing-library/jest-dom';
import { vi } from 'vitest';

// Polyfill scrollIntoView for jsdom environment
if (typeof window !== 'undefined') {
  window.HTMLElement.prototype.scrollIntoView = vi.fn();
}

