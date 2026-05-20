import { create } from 'zustand'
import { persist } from 'zustand/middleware'

const useAuthStore = create(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isLoggedIn: false,

      setAuth: (user, token) => set({
        user, token, isLoggedIn: true
      }),

      logout: () => set({
        user: null, token: null, isLoggedIn: false
      }),

      updateUser: (updates) => set(state => ({
        user: { ...state.user, ...updates }
      })),
    }),
    {
      name: 'byus-auth',   // persisted in localStorage
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        isLoggedIn: state.isLoggedIn
      })
    }
  )
)

export default useAuthStore
