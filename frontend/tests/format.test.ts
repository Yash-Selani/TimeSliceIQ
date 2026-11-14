import { describe, expect, it } from 'vitest';
import { secondsToLabel, secondsToSpoken } from '../src/lib/format';

describe('secondsToLabel', () => {
  it('formats under 1 hour in MM:SS', () => {
    expect(secondsToLabel(0)).toBe('00:00');
    expect(secondsToLabel(5)).toBe('00:05');
    expect(secondsToLabel(59)).toBe('00:59');
    expect(secondsToLabel(60)).toBe('01:00');
    expect(secondsToLabel(75)).toBe('01:15');
    expect(secondsToLabel(765)).toBe('12:45');
    expect(secondsToLabel(3599)).toBe('59:59');
  });

  it('formats 1 hour or more in HH:MM:SS', () => {
    expect(secondsToLabel(3600)).toBe('01:00:00');
    expect(secondsToLabel(3665)).toBe('01:01:05');
    expect(secondsToLabel(7325)).toBe('02:02:05');
    expect(secondsToLabel(36000)).toBe('10:00:00');
  });

  it('handles floats and edge cases safely', () => {
    expect(secondsToLabel(75.8)).toBe('01:15');
    expect(secondsToLabel(-10)).toBe('00:00');
    expect(secondsToLabel(NaN)).toBe('00:00');
    expect(secondsToLabel(Infinity)).toBe('00:00');
  });
});

describe('secondsToSpoken', () => {
  it('formats zero seconds', () => {
    expect(secondsToSpoken(0)).toBe('00 seconds'.replace('00', '0'));
  });

  it('formats under 1 hour', () => {
    expect(secondsToSpoken(1)).toBe('1 second');
    expect(secondsToSpoken(15)).toBe('15 seconds');
    expect(secondsToSpoken(60)).toBe('1 minute');
    expect(secondsToSpoken(61)).toBe('1 minute 1 second');
    expect(secondsToSpoken(75)).toBe('1 minute 15 seconds');
    expect(secondsToSpoken(765)).toBe('12 minutes 45 seconds');
  });

  it('formats 1 hour or more', () => {
    expect(secondsToSpoken(3600)).toBe('1 hour');
    expect(secondsToSpoken(3601)).toBe('1 hour 1 second');
    expect(secondsToSpoken(3665)).toBe('1 hour 1 minute 5 seconds');
    expect(secondsToSpoken(7200)).toBe('2 hours');
    expect(secondsToSpoken(7325)).toBe('2 hours 2 minutes 5 seconds');
  });

  it('handles floats and negative values safely', () => {
    expect(secondsToSpoken(75.9)).toBe('1 minute 15 seconds');
    expect(secondsToSpoken(-5)).toBe('0 seconds');
    expect(secondsToSpoken(NaN)).toBe('0 seconds');
    expect(secondsToSpoken(Infinity)).toBe('0 seconds');
  });
});
