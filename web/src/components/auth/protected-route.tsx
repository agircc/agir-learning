"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/lib/auth-context"
import { Loader2 } from "lucide-react"

interface ProtectedRouteProps {
  children: React.ReactNode
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const router = useRouter()
  const { user, isLoading, validateToken } = useAuth()

  useEffect(() => {
    const checkAuth = async () => {
      if (!isLoading) {
        if (!user) {
          // User is not logged in, redirect to login
          router.replace("/login")
        } else {
          // Validate token
          const isValid = await validateToken()
          if (!isValid) {
            // Token is invalid, redirect to login
            router.replace("/login")
          }
        }
      }
    }

    checkAuth()
  }, [isLoading, user, router, validateToken])

  // Show loading screen while checking authentication
  if (isLoading) {
    return (
      <div className="flex justify-center items-center min-h-[calc(100vh-4rem)]">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    )
  }

  // If not authenticated, don't render children (will redirect in useEffect)
  if (!user) {
    return null
  }

  // User is authenticated, render children
  return <>{children}</>
} 