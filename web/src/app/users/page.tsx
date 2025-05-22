"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { usersAPI } from "@/lib/api"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ArrowRight, Loader2, Search, User } from "lucide-react"

interface User {
  id: string
  username: string
  email: string
  first_name: string
  last_name: string
  full_name: string
  role: string
  created_at: string
}

export default function UsersPage() {
  const router = useRouter()
  const [users, setUsers] = useState<User[]>([])
  const [filteredUsers, setFilteredUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState("")

  useEffect(() => {
    const fetchUsers = async () => {
      try {
        setLoading(true)
        const data = await usersAPI.getAll()
        setUsers(data)
        setFilteredUsers(data)
        setError(null)
      } catch (err) {
        console.error("Failed to fetch users:", err)
        setError("Failed to load users. Please try again later.")
      } finally {
        setLoading(false)
      }
    }

    fetchUsers()
  }, [])

  useEffect(() => {
    if (searchQuery.trim() === "") {
      setFilteredUsers(users)
      return
    }

    const query = searchQuery.toLowerCase()
    const filtered = users.filter(
      (user) =>
        user.username.toLowerCase().includes(query) ||
        (user.full_name && user.full_name.toLowerCase().includes(query)) ||
        (user.email && user.email.toLowerCase().includes(query))
    )
    setFilteredUsers(filtered)
  }, [searchQuery, users])

  const handleViewUser = (id: string) => {
    router.push(`/users/${id}`)
  }

  return (
    <div className="container mx-auto py-10">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-8">
        <h1 className="text-3xl font-bold tracking-tight">Users</h1>
        <div className="relative w-full sm:w-64">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            type="search"
            placeholder="Search users..."
            className="pl-8"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center items-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : error ? (
        <div className="rounded-lg border border-destructive bg-destructive/10 p-4">
          <p className="text-destructive">{error}</p>
        </div>
      ) : filteredUsers.length === 0 ? (
        <div className="rounded-lg border border-border p-8 text-center">
          <p className="text-muted-foreground">No users found.</p>
        </div>
      ) : (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Username</TableHead>
                <TableHead className="hidden md:table-cell">Name</TableHead>
                <TableHead className="hidden md:table-cell">Role</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredUsers.map((user) => (
                <TableRow key={user.id}>
                  <TableCell className="font-medium">
                    <div className="flex items-center gap-2">
                      <User className="h-4 w-4 text-muted-foreground" />
                      {user.username}
                    </div>
                  </TableCell>
                  <TableCell className="hidden md:table-cell">
                    {user.full_name || "-"}
                  </TableCell>
                  <TableCell className="hidden md:table-cell">
                    {user.role || "-"}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleViewUser(user.id)}
                    >
                      View
                      <ArrowRight className="ml-2 h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  )
} 