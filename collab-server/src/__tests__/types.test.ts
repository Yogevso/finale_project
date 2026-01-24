/**
 * Unit Tests for Types and Utilities
 */

import { getUserColor, USER_COLORS } from '../types.js';

describe('Types and Utilities', () => {
  describe('getUserColor', () => {
    it('should return a valid color from the palette', () => {
      const color = getUserColor('user123');
      expect(USER_COLORS).toContain(color);
    });

    it('should return consistent color for same user ID', () => {
      const userId = 'consistent-user-42';
      const color1 = getUserColor(userId);
      const color2 = getUserColor(userId);
      const color3 = getUserColor(userId);

      expect(color1).toBe(color2);
      expect(color2).toBe(color3);
    });

    it('should return different colors for different users (usually)', () => {
      // Test with many users - statistically they should get different colors
      const colors = new Set<string>();
      for (let i = 0; i < 20; i++) {
        colors.add(getUserColor(`user-${i}`));
      }
      // With 16 colors and 20 users, we should have at least 5 different colors
      expect(colors.size).toBeGreaterThanOrEqual(5);
    });

    it('should handle numeric user IDs', () => {
      const color = getUserColor('1');
      expect(typeof color).toBe('string');
      expect(color.startsWith('#')).toBe(true);
    });

    it('should handle empty string', () => {
      const color = getUserColor('');
      expect(USER_COLORS).toContain(color);
    });
  });

  describe('USER_COLORS', () => {
    it('should have at least 10 colors', () => {
      expect(USER_COLORS.length).toBeGreaterThanOrEqual(10);
    });

    it('should all be valid hex colors', () => {
      const hexColorRegex = /^#[0-9A-Fa-f]{6}$/;
      for (const color of USER_COLORS) {
        expect(color).toMatch(hexColorRegex);
      }
    });

    it('should have unique colors', () => {
      const uniqueColors = new Set(USER_COLORS);
      expect(uniqueColors.size).toBe(USER_COLORS.length);
    });
  });
});
