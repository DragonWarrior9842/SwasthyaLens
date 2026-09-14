import { createContext, useContext } from 'react'
import type { AuthState, Session } from '../../types/auth'

export interface AuthContextValue {
  state: AuthState
  pendingEmail: string
  notice: string | null
  setPendingEmail: (email: string) => void
  acceptSession: (session: Session) => void
  checkSession: () => Promise<void>
  logout: () => Promise<void>
}

export const AuthContext = createContext<AuthContextValue | null>(null)

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext)
  if (!value) throw new Error('Authentication provider is missing.')
  return value
}
