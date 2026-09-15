/** A refresh can retain its short expiry when the absolute session limit is near. */
export function sessionCheckDelay(expiresAt: number, now = Date.now()): number {
  const remaining = expiresAt * 1000 - now
  // Session restoration already attempts refresh inside this final minute. Waiting
  // for expiry avoids repeatedly rotating tokens that cannot extend the session.
  return Math.max(1_000, remaining <= 60_000 ? remaining + 1_000 : remaining - 45_000)
}
