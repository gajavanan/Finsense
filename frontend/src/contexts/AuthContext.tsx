import { createContext, useContext } from 'react'
import { useAuthStore } from '../store/authStore'
export const AuthContext = createContext<any>(null)
export const useAuth = ()=> useContext(AuthContext)
