"use client"

import React, { createContext, useContext, useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { authAPI } from "./api"

interface User {
  id: string
  email: string
  username: string
  first_name: string
  last_name: string
  token: string
}

interface AuthContextType {
  user: User | null
  isLoading: boolean
  login: (userData: User) => void
  logout: () => void
  validateToken: () => Promise<boolean>
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  isLoading: true,
  login: () => { },
  logout: () => { },
  validateToken: async () => false,
})

export const useAuth = () => useContext(AuthContext)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const initAuth = async () => {
      // Check if user data exists in localStorage
      const storedUser = localStorage.getItem("user")
      if (storedUser) {
        try {
          const userData = JSON.parse(storedUser)

          // Validate the token
          if (userData.token) {
            const isValid = await validateStoredToken(userData.token)
            if (isValid) {
              setUser(userData)
            } else {
              // Token is invalid, clear user data
              localStorage.removeItem("user")
            }
          }
        } catch (error) {
          console.error("Failed to parse user data from localStorage", error)
          localStorage.removeItem("user")
        }
      }
      setIsLoading(false)
    }

    initAuth()
  }, [])

  const validateStoredToken = async (token: string): Promise<boolean> => {
    try {
      const response = await authAPI.validateToken(token)
      return response.valid
    } catch (error) {
      console.error("Token validation failed:", error)
      return false
    }
  }

  const validateToken = async (): Promise<boolean> => {
    if (!user || !user.token) return false
    return validateStoredToken(user.token)
  }

  const login = (userData: User) => {
    setUser(userData)
    localStorage.setItem("user", JSON.stringify(userData))
  }

  const logout = () => {
    setUser(null)
    localStorage.removeItem("user")
    router.push("/login")
  }

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout, validateToken }}>
      {children}
    </AuthContext.Provider>
  )
} 