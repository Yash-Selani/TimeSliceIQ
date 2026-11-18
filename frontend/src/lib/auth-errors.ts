/**
 * Human-readable mapping and sanitization for Firebase Authentication errors.
 */

export function formatAuthError(err: unknown): string | null {
  if (!err) return null;

  const rawMsg = err instanceof Error ? err.message : String(err);
  const code = (err as { code?: string })?.code || '';

  // 1. User intentionally closed or dismissed the popup — benign, ignore silently
  if (
    code === 'auth/popup-closed-by-user' ||
    code === 'auth/cancelled-popup-request' ||
    rawMsg.includes('popup-closed-by-user') ||
    rawMsg.includes('cancelled-popup-request')
  ) {
    return null;
  }

  // 2. Popup blocked by browser settings/adblock
  if (code === 'auth/popup-blocked' || rawMsg.includes('popup-blocked')) {
    return 'The sign-in popup was blocked by your browser. Please allow popups for this site.';
  }

  // 3. Domain not authorized in Firebase Console
  if (code === 'auth/unauthorized-domain' || rawMsg.includes('unauthorized-domain')) {
    return 'This domain is not yet authorized in Firebase Console. Please add your domain to Authorized Domains in Firebase Console > Authentication > Settings.';
  }

  // 4. Provider not enabled
  if (code === 'auth/operation-not-allowed' || rawMsg.includes('operation-not-allowed')) {
    return 'This sign-in method is not enabled. Please enable Google / Email in Firebase Console > Authentication > Sign-in method.';
  }

  // 5. Invalid credentials / user not found / wrong password
  if (
    code === 'auth/invalid-credential' ||
    code === 'auth/wrong-password' ||
    code === 'auth/user-not-found' ||
    rawMsg.includes('invalid-credential') ||
    rawMsg.includes('wrong-password') ||
    rawMsg.includes('user-not-found')
  ) {
    return 'Incorrect email or password. Please verify your credentials.';
  }

  // 6. Email already registered
  if (code === 'auth/email-already-in-use' || rawMsg.includes('email-already-in-use')) {
    return 'An account already exists with this email address. Please sign in instead.';
  }

  // 7. Weak password
  if (code === 'auth/weak-password' || rawMsg.includes('weak-password')) {
    return 'Password is too weak. Please use at least 6 characters.';
  }

  // 8. Invalid email format
  if (code === 'auth/invalid-email' || rawMsg.includes('invalid-email')) {
    return 'Please enter a valid email address.';
  }

  // 9. Network error
  if (code === 'auth/network-request-failed' || rawMsg.includes('network-request-failed')) {
    return 'Network connection issue. Please check your internet connection.';
  }

  // 10. Clean up raw Firebase error prefix
  const cleaned = rawMsg.replace(/^Firebase:\s*Error\s*\(([^)]+)\)\.?/i, '$1').trim();
  return cleaned || 'Authentication failed. Please try again.';
}
