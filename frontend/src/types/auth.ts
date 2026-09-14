export interface Session {
  user: { id: string; email: string }
  expires_at: number
}

export interface Profile {
  id: string
  display_name: string | null
  created_at: string
  updated_at: string
}

export interface UserSettings {
  user_id: string
  preferred_language: 'en' | 'hi'
  timezone: string
  created_at: string
  updated_at: string
}

export type AuthState =
  | { status: 'checking' }
  | { status: 'authenticated'; session: Session }
  | { status: 'anonymous' }
  | { status: 'unavailable'; message: string }
