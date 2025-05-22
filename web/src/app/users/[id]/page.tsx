"use client"

import { useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { usersAPI, memoriesAPI } from "@/lib/api"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Loader2, ArrowLeft, MessageSquare } from "lucide-react"
import Link from "next/link"
import { ProtectedRoute } from "@/components/auth/protected-route"
import { Pagination } from "@/components/ui/pagination"

interface User {
  id: string
  username: string
  email: string
  first_name: string
  last_name: string
  full_name: string
  created_at: string
  updated_at: string
  avatar?: string
  description?: string
}

interface Memory {
  id: string
  content: string
  memory_type: string
  importance: number
  created_at: string
}

export default function UserDetailsPage() {
  const router = useRouter()
  const params = useParams()
  const id = params.id as string
  const [user, setUser] = useState<User | null>(null)
  const [memories, setMemories] = useState<Memory[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [memoriesPage, setMemoriesPage] = useState(1)
  const [memoriesPageCount, setMemoriesPageCount] = useState(1)
  const [memoriesTotal, setMemoriesTotal] = useState(0)

  useEffect(() => {
    const fetchUserData = async () => {
      try {
        setLoading(true)
        const userData = await usersAPI.getById(id)
        setUser(userData)

        const memoriesData = await memoriesAPI.getByUserId(id, memoriesPage, 10)
        setMemories(memoriesData.items)
        setMemoriesPageCount(memoriesData.pages)
        setMemoriesTotal(memoriesData.total)

        setError(null)
      } catch (err) {
        console.error("Failed to fetch user data:", err)
        setError("Failed to load user details. Please try again later.")
      } finally {
        setLoading(false)
      }
    }

    if (id) {
      fetchUserData()
    }
  }, [id, memoriesPage])

  const handleChatClick = () => {
    router.push(`/chat/${user?.id}`)
  }

  const handlePageChange = (page: number) => {
    setMemoriesPage(page)
  }

  if (loading) {
    return (
      <ProtectedRoute>
        <div className="container mx-auto py-10">
          <div className="flex justify-center items-center h-64">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        </div>
      </ProtectedRoute>
    )
  }

  if (error) {
    return (
      <ProtectedRoute>
        <div className="container mx-auto py-10">
          <div className="rounded-lg border border-destructive bg-destructive/10 p-4">
            <p className="text-destructive">{error}</p>
          </div>
        </div>
      </ProtectedRoute>
    )
  }

  if (!user) {
    return (
      <ProtectedRoute>
        <div className="container mx-auto py-10">
          <div className="rounded-lg border border-border p-8 text-center">
            <p className="text-muted-foreground">User not found.</p>
          </div>
        </div>
      </ProtectedRoute>
    )
  }

  return (
    <ProtectedRoute>
      <div className="container mx-auto py-10">
        <div className="mb-6">
          <Button variant="outline" size="sm" asChild>
            <Link href="/users">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Users
            </Link>
          </Button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card className="md:col-span-1">
            <CardHeader>
              <CardTitle className="text-2xl">User Profile</CardTitle>
              <CardDescription>
                Created: {new Date(user.created_at).toLocaleDateString()}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="mb-6 space-y-2">
                <h3 className="text-lg font-medium">Details</h3>
                <div className="grid grid-cols-1 gap-1">
                  <div><strong>Username:</strong> {user.username}</div>
                  <div><strong>Name:</strong> {user.full_name || "Not provided"}</div>
                  <div><strong>Email:</strong> {user.email || "Not provided"}</div>
                  {user.description && (
                    <div className="mt-2">
                      <strong>Description:</strong>
                      <p className="mt-1">{user.description}</p>
                    </div>
                  )}
                </div>
              </div>

              <Button
                className="w-full"
                onClick={handleChatClick}
              >
                <MessageSquare className="mr-2 h-4 w-4" />
                Chat with User
              </Button>
            </CardContent>
          </Card>

          <Card className="md:col-span-2">
            <CardHeader>
              <CardTitle className="flex justify-between items-center">
                <span>Memories</span>
                <span className="text-sm font-normal text-muted-foreground">
                  Total: {memoriesTotal}
                </span>
              </CardTitle>
              <CardDescription>User&apos;s memories and reflections</CardDescription>
            </CardHeader>
            <CardContent>
              {memories.length === 0 ? (
                <div className="text-center p-4 bg-muted/40 rounded-md">
                  <p className="text-muted-foreground">No memories available for this user.</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {memories.map((memory) => (
                    <Card key={memory.id} className="bg-muted/40">
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm flex justify-between items-center">
                          <span>{memory.memory_type}</span>
                          <span className="text-xs px-2 py-1 bg-primary/10 text-primary rounded-md">
                            Importance: {memory.importance.toFixed(1)}
                          </span>
                        </CardTitle>
                        <CardDescription>
                          {new Date(memory.created_at).toLocaleDateString()}
                        </CardDescription>
                      </CardHeader>
                      <CardContent>
                        <p>{memory.content}</p>
                      </CardContent>
                    </Card>
                  ))}

                  {memoriesPageCount > 1 && (
                    <Pagination
                      currentPage={memoriesPage}
                      totalPages={memoriesPageCount}
                      onPageChange={handlePageChange}
                    />
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </ProtectedRoute>
  )
} 