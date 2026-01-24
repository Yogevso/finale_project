/**
 * User colors for collaboration cursors
 * Provides consistent color assignment based on user ID
 */

export const USER_COLORS = [
  { name: 'Red', color: '#F44336', light: '#FFEBEE' },
  { name: 'Pink', color: '#E91E63', light: '#FCE4EC' },
  { name: 'Purple', color: '#9C27B0', light: '#F3E5F5' },
  { name: 'Deep Purple', color: '#673AB7', light: '#EDE7F6' },
  { name: 'Indigo', color: '#3F51B5', light: '#E8EAF6' },
  { name: 'Blue', color: '#2196F3', light: '#E3F2FD' },
  { name: 'Light Blue', color: '#03A9F4', light: '#E1F5FE' },
  { name: 'Cyan', color: '#00BCD4', light: '#E0F7FA' },
  { name: 'Teal', color: '#009688', light: '#E0F2F1' },
  { name: 'Green', color: '#4CAF50', light: '#E8F5E9' },
  { name: 'Light Green', color: '#8BC34A', light: '#F1F8E9' },
  { name: 'Lime', color: '#CDDC39', light: '#F9FBE7' },
  { name: 'Amber', color: '#FFC107', light: '#FFF8E1' },
  { name: 'Orange', color: '#FF9800', light: '#FFF3E0' },
  { name: 'Deep Orange', color: '#FF5722', light: '#FBE9E7' },
];

/**
 * Get a consistent color for a user based on their ID
 */
export function getUserColor(userId: string | number): { name: string; color: string; light: string } {
  const id = typeof userId === 'string' ? userId : String(userId);
  let hash = 0;
  for (let i = 0; i < id.length; i++) {
    hash = id.charCodeAt(i) + ((hash << 5) - hash);
  }
  return USER_COLORS[Math.abs(hash) % USER_COLORS.length];
}

/**
 * Get just the color hex value for a user
 */
export function getUserColorHex(userId: string | number): string {
  return getUserColor(userId).color;
}

/**
 * Get the light background color for a user (for highlights)
 */
export function getUserColorLight(userId: string | number): string {
  return getUserColor(userId).light;
}

/**
 * Generate a random color for anonymous users
 */
export function getRandomColor(): { name: string; color: string; light: string } {
  return USER_COLORS[Math.floor(Math.random() * USER_COLORS.length)];
}
