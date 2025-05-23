"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { usersAPI } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  ArrowRight,
  Loader2,
  Search,
  User as UserIcon,
  Briefcase,
  Mail
} from "lucide-react"
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
  PaginationEllipsis,
} from "@/components/ui/pagination"

interface User {
  id: string
  username: string
  email: string
  first_name: string
  last_name: string
  full_name: string
  avatar?: string
  profession?: string
  description?: string
  created_at: string
}

interface UsersResponse {
  items: User[]
  total: number
  page: number
  size: number
  pages: number
}

export default function UsersPage() {
  const router = useRouter()
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState("")
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [totalUsers, setTotalUsers] = useState(0)
  const pageSize = 12

  useEffect(() => {
    const fetchUsers = async () => {
      try {
        setLoading(true)
        const data: UsersResponse = await usersAPI.getAll(
          currentPage,
          pageSize,
          searchQuery.trim() || undefined
        )
        setUsers(data.items)
        setTotalPages(data.pages)
        setTotalUsers(data.total)
        setError(null)
      } catch (err) {
        console.error("Failed to fetch users:", err)
        setError("Failed to load users. Please try again later.")
      } finally {
        setLoading(false)
      }
    }

    fetchUsers()
  }, [currentPage, searchQuery])

  const handleSearch = (value: string) => {
    setSearchQuery(value)
    setCurrentPage(1) // Reset to first page when searching
  }

  const handlePageChange = (page: number) => {
    setCurrentPage(page)
  }

  const handleViewUser = (id: string) => {
    router.push(`/users/${id}`)
  }

  // Generate initials for avatar fallback
  const getInitials = (user: User) => {
    if (user.first_name && user.last_name) {
      return `${user.first_name[0]}${user.last_name[0]}`.toUpperCase()
    }
    return user.username.substring(0, 2).toUpperCase()
  }

  // Generate pagination items
  const getPaginationItems = () => {
    const items = []
    const maxVisible = 5

    if (totalPages <= maxVisible) {
      for (let i = 1; i <= totalPages; i++) {
        items.push(i)
      }
    } else {
      if (currentPage <= 3) {
        items.push(1, 2, 3, 4, "ellipsis", totalPages)
      } else if (currentPage >= totalPages - 2) {
        items.push(1, "ellipsis", totalPages - 3, totalPages - 2, totalPages - 1, totalPages)
      } else {
        items.push(1, "ellipsis", currentPage - 1, currentPage, currentPage + 1, "ellipsis", totalPages)
      }
    }

    return items
  }

  return (
    <div className="container mx-auto py-10">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Users</h1>
          <p className="text-muted-foreground mt-1">
            {totalUsers} user{totalUsers !== 1 ? 's' : ''} total
          </p>
        </div>
        <div className="relative w-full sm:w-64">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            type="search"
            placeholder="Search users..."
            className="pl-8"
            value={searchQuery}
            onChange={(e) => handleSearch(e.target.value)}
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
      ) : users.length === 0 ? (
        <div className="rounded-lg border border-border p-8 text-center">
          <p className="text-muted-foreground">
            {searchQuery ? `No users found matching "${searchQuery}".` : "No users found."}
          </p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {users.map((user) => (
              <Card key={user.id} className="overflow-hidden">
                <CardHeader className="p-4 pb-0 flex flex-row items-center gap-4">
                  <Avatar className="h-14 w-14">
                    <AvatarImage src={user.avatar || ""} alt={user.full_name || user.username} />
                    <AvatarFallback className="text-lg">{getInitials(user)}</AvatarFallback>
                  </Avatar>
                  <div className="flex-1 min-w-0">
                    <h3 className="text-xl font-semibold mb-1 truncate">{user.full_name || user.username}</h3>
                    {user.profession && (
                      <div className="flex items-center text-sm text-muted-foreground">
                        <Briefcase className="mr-1 h-3 w-3 flex-shrink-0" />
                        <span className="truncate">{user.profession}</span>
                      </div>
                    )}
                  </div>
                </CardHeader>
                <CardContent className="p-4">
                  <div className="flex flex-col gap-2 text-sm">
                    <div className="flex items-center gap-2">
                      <UserIcon className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                      <span className="text-muted-foreground truncate">@{user.username}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Mail className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                      <span className="text-muted-foreground truncate">{user.email}</span>
                    </div>
                    {user.description && (
                      <p className="mt-2 line-clamp-2 text-muted-foreground">
                        {user.description}
                      </p>
                    )}
                  </div>
                </CardContent>
                <CardFooter className="p-4 pt-0 flex justify-end">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleViewUser(user.id)}
                  >
                    View Profile
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                </CardFooter>
              </Card>
            ))}
          </div>

          {totalPages > 1 && (
            <div className="mt-8 flex justify-center">
              <Pagination>
                <PaginationContent>
                  <PaginationItem>
                    <PaginationPrevious
                      href="#"
                      onClick={(e) => {
                        e.preventDefault()
                        if (currentPage > 1) handlePageChange(currentPage - 1)
                      }}
                      className={currentPage <= 1 ? "pointer-events-none opacity-50" : ""}
                    />
                  </PaginationItem>

                  {getPaginationItems().map((item, index) => (
                    <PaginationItem key={index}>
                      {item === "ellipsis" ? (
                        <PaginationEllipsis />
                      ) : (
                        <PaginationLink
                          href="#"
                          onClick={(e) => {
                            e.preventDefault()
                            handlePageChange(item as number)
                          }}
                          isActive={currentPage === item}
                        >
                          {item}
                        </PaginationLink>
                      )}
                    </PaginationItem>
                  ))}

                  <PaginationItem>
                    <PaginationNext
                      href="#"
                      onClick={(e) => {
                        e.preventDefault()
                        if (currentPage < totalPages) handlePageChange(currentPage + 1)
                      }}
                      className={currentPage >= totalPages ? "pointer-events-none opacity-50" : ""}
                    />
                  </PaginationItem>
                </PaginationContent>
              </Pagination>
            </div>
          )}
        </>
      )}
    </div>
  )
} 