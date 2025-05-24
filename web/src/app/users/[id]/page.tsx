"use client"

import { useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { usersAPI, memoriesAPI } from "@/lib/api"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Loader2, ArrowLeft, MessageSquare, BookOpen, FlaskConical, Clock, CalendarDays, Info, GraduationCap } from "lucide-react"
import Link from "next/link"
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious
} from "@/components/ui/pagination"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { cn } from "@/lib/utils"

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
  source?: string
  meta_data?: {
    // Episode-related metadata
    episode_id?: string
    scenario_id?: string
    scenario_name?: string

    // Book reading metadata
    book_title?: string
    importance_score?: number
    memory_type?: string
    read_date?: string
  }
}

interface Episode {
  id: string
  scenario_id: string
  status: string
  created_at: string
  updated_at: string
  scenario_name?: string
  role_description?: string
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
  const [episodes, setEpisodes] = useState<Episode[]>([])
  const [episodesLoading, setEpisodesLoading] = useState(false)
  const [episodesPage, setEpisodesPage] = useState(1)
  const [episodesPageCount, setEpisodesPageCount] = useState(1)
  const [episodesTotal, setEpisodesTotal] = useState(0)
  const [learningEpisodes, setLearningEpisodes] = useState<Episode[]>([])
  const [learningLoading, setLearningLoading] = useState(false)
  const [learningPage, setLearningPage] = useState(1)
  const [learningPageCount, setLearningPageCount] = useState(1)
  const [learningTotal, setLearningTotal] = useState(0)

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

  const fetchEpisodes = async () => {
    try {
      setEpisodesLoading(true)
      const episodesData = await usersAPI.getEpisodes(id, episodesPage, 10)
      setEpisodes(episodesData.items)
      setEpisodesPageCount(episodesData.pages)
      setEpisodesTotal(episodesData.total)
    } catch (err) {
      console.error("Failed to fetch episodes:", err)
    } finally {
      setEpisodesLoading(false)
    }
  }

  const fetchLearningEpisodes = async () => {
    try {
      setLearningLoading(true)
      const learningData = await usersAPI.getLearningEpisodes(id, learningPage, 10)
      setLearningEpisodes(learningData.items)
      setLearningPageCount(learningData.pages)
      setLearningTotal(learningData.total)
    } catch (err) {
      console.error("Failed to fetch learning episodes:", err)
    } finally {
      setLearningLoading(false)
    }
  }

  const handleChatClick = () => {
    router.push(`/chat/${user?.id}`)
  }

  const handlePageChange = (page: number) => {
    setMemoriesPage(page)
  }

  const handleEpisodesPageChange = (page: number) => {
    setEpisodesPage(page)
  }

  const handleLearningPageChange = (page: number) => {
    setLearningPage(page)
  }

  // Fetch episodes when page changes
  useEffect(() => {
    if (episodesPage > 1 && episodes.length > 0) {
      fetchEpisodes()
    }
  }, [episodesPage])

  // Fetch learning episodes when page changes
  useEffect(() => {
    if (learningPage > 1 && learningEpisodes.length > 0) {
      fetchLearningEpisodes()
    }
  }, [learningPage])

  if (loading) {
    return (
      <div className="container mx-auto py-10">
        <div className="flex justify-center items-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="container mx-auto py-10">
        <div className="rounded-lg border border-destructive bg-destructive/10 p-4">
          <p className="text-destructive">{error}</p>
        </div>
      </div>
    )
  }

  if (!user) {
    return (
      <div className="container mx-auto py-10">
        <div className="rounded-lg border border-border p-8 text-center">
          <p className="text-muted-foreground">User not found.</p>
        </div>
      </div>
    )
  }

  return (
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
        {/* User Profile Sidebar */}
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

        {/* Main Content with Tabs */}
        <div className="md:col-span-2">
          <Tabs defaultValue="memories" className="w-full" onValueChange={(value) => {
            if (value === "episodes" && episodes.length === 0) {
              fetchEpisodes()
            }
            if (value === "learning" && learningEpisodes.length === 0) {
              fetchLearningEpisodes()
            }
          }}>
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="memories" className="flex items-center gap-2">
                <BookOpen className="h-4 w-4" />
                Memories ({memoriesTotal})
              </TabsTrigger>
              <TabsTrigger value="episodes" className="flex items-center gap-2">
                <FlaskConical className="h-4 w-4" />
                Episodes ({episodesTotal})
              </TabsTrigger>
              <TabsTrigger value="learning" className="flex items-center gap-2">
                <GraduationCap className="h-4 w-4" />
                Learning ({learningTotal})
              </TabsTrigger>
            </TabsList>

            <TabsContent value="memories" className="mt-6">
              <Card>
                <CardHeader>
                  <CardTitle>Memories</CardTitle>
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
                        <Card key={memory.id} className={cn(
                          "overflow-hidden transition-all hover:shadow-md",
                          memory.source === "book_reading_record" ? "border-l-4 border-l-blue-500/50" :
                            memory.source === "episode" ? "border-l-4 border-l-green-500/50" : ""
                        )}>
                          <CardHeader className="pb-2 relative">
                            <div className="flex items-start justify-between">
                              <div className="flex items-center gap-2">
                                {memory.source === "book_reading_record" && (
                                  <BookOpen className="h-4 w-4 text-blue-500" />
                                )}
                                {memory.source === "episode" && (
                                  <FlaskConical className="h-4 w-4 text-green-500" />
                                )}
                                <Badge variant="outline" className="font-normal">
                                  {memory.memory_type}
                                </Badge>
                              </div>
                              <div className="flex items-center gap-1">
                                <Info className="h-3 w-3 text-muted-foreground" />
                                <span className="text-xs px-2 py-1 bg-primary/10 text-primary rounded-md font-medium">
                                  {memory.importance.toFixed(1)}
                                </span>
                              </div>
                            </div>
                            <CardDescription className="flex items-center mt-2 text-xs gap-1">
                              <Clock className="h-3 w-3" />
                              {new Date(memory.created_at).toLocaleDateString()} {new Date(memory.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </CardDescription>
                          </CardHeader>
                          <CardContent>
                            <p className="whitespace-pre-wrap leading-relaxed">{memory.content}</p>

                            {memory.source && memory.meta_data && (
                              <div className="mt-4 pt-3 border-t text-xs text-muted-foreground">
                                {memory.source === "episode" && (
                                  <div className="space-y-2">
                                    <div className="flex items-center gap-1.5">
                                      <FlaskConical className="h-3.5 w-3.5" />
                                      <span className="font-medium">From Simulation</span>
                                    </div>

                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-1.5 pl-1">
                                      {memory.meta_data.scenario_name && (
                                        <div className="col-span-full">
                                          <span className="text-muted-foreground">Scenario: </span>
                                          <span className="text-foreground">{memory.meta_data.scenario_name}</span>
                                        </div>
                                      )}
                                      {memory.meta_data.scenario_id && (
                                        <div className="flex items-center gap-1">
                                          <span className="text-muted-foreground">Scenario ID: </span>
                                          <Link
                                            href={`/scenarios/${memory.meta_data.scenario_id}`}
                                            className="text-primary hover:underline"
                                          >
                                            View
                                          </Link>
                                        </div>
                                      )}
                                      {memory.meta_data.episode_id && (
                                        <div className="flex items-center gap-1">
                                          <span className="text-muted-foreground">Episode ID: </span>
                                          <Link
                                            href={`/episodes/${memory.meta_data.episode_id}`}
                                            className="text-primary hover:underline"
                                          >
                                            View
                                          </Link>
                                        </div>
                                      )}
                                    </div>
                                  </div>
                                )}

                                {memory.source === "book_reading_record" && (
                                  <div className="space-y-2">
                                    <div className="flex items-center gap-1.5">
                                      <BookOpen className="h-3.5 w-3.5" />
                                      <span className="font-medium">From Book Reading</span>
                                    </div>

                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-1.5 pl-1">
                                      {memory.meta_data.book_title && (
                                        <div className="col-span-full">
                                          <span className="text-muted-foreground">Book: </span>
                                          <span className="text-foreground font-medium">{memory.meta_data.book_title}</span>
                                        </div>
                                      )}
                                      {memory.meta_data.memory_type && (
                                        <div>
                                          <span className="text-muted-foreground">Type: </span>
                                          <span>{memory.meta_data.memory_type}</span>
                                        </div>
                                      )}
                                      {memory.meta_data.importance_score !== undefined && (
                                        <div>
                                          <span className="text-muted-foreground">Importance: </span>
                                          <span>{memory.meta_data.importance_score}</span>
                                        </div>
                                      )}
                                      {memory.meta_data.read_date && (
                                        <div className="col-span-full flex items-center gap-1">
                                          <CalendarDays className="h-3 w-3" />
                                          <span className="text-muted-foreground">Read on: </span>
                                          <span>{new Date(memory.meta_data.read_date).toLocaleDateString()} {new Date(memory.meta_data.read_date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                                        </div>
                                      )}
                                    </div>
                                  </div>
                                )}
                              </div>
                            )}
                          </CardContent>
                        </Card>
                      ))}

                      {memoriesPageCount > 1 && (
                        <Pagination className="mt-6">
                          <PaginationContent>
                            <PaginationItem>
                              <PaginationPrevious
                                href="#"
                                onClick={(e) => {
                                  e.preventDefault()
                                  if (memoriesPage > 1) handlePageChange(memoriesPage - 1)
                                }}
                                className={memoriesPage <= 1 ? "pointer-events-none opacity-50" : ""}
                              />
                            </PaginationItem>

                            {memoriesPageCount <= 7 ? (
                              [...Array(memoriesPageCount)].map((_, i) => (
                                <PaginationItem key={i}>
                                  <PaginationLink
                                    href="#"
                                    onClick={(e) => {
                                      e.preventDefault()
                                      handlePageChange(i + 1)
                                    }}
                                    isActive={memoriesPage === i + 1}
                                  >
                                    {i + 1}
                                  </PaginationLink>
                                </PaginationItem>
                              ))
                            ) : (
                              <>
                                <PaginationItem>
                                  <PaginationLink
                                    href="#"
                                    onClick={(e) => {
                                      e.preventDefault()
                                      handlePageChange(1)
                                    }}
                                    isActive={memoriesPage === 1}
                                  >
                                    1
                                  </PaginationLink>
                                </PaginationItem>

                                {memoriesPage > 3 && (
                                  <PaginationItem>
                                    <div className="flex h-9 w-9 items-center justify-center">
                                      …
                                    </div>
                                  </PaginationItem>
                                )}

                                {Array.from({ length: 3 }, (_, i) => {
                                  const pageNumber = Math.min(
                                    Math.max(memoriesPage + i - 1, 2),
                                    memoriesPageCount - 1
                                  )

                                  if (pageNumber === 1 || pageNumber === memoriesPageCount) {
                                    return null
                                  }

                                  return (
                                    <PaginationItem key={pageNumber}>
                                      <PaginationLink
                                        href="#"
                                        onClick={(e) => {
                                          e.preventDefault()
                                          handlePageChange(pageNumber)
                                        }}
                                        isActive={memoriesPage === pageNumber}
                                      >
                                        {pageNumber}
                                      </PaginationLink>
                                    </PaginationItem>
                                  )
                                })}

                                {memoriesPage < memoriesPageCount - 2 && (
                                  <PaginationItem>
                                    <div className="flex h-9 w-9 items-center justify-center">
                                      …
                                    </div>
                                  </PaginationItem>
                                )}

                                <PaginationItem>
                                  <PaginationLink
                                    href="#"
                                    onClick={(e) => {
                                      e.preventDefault()
                                      handlePageChange(memoriesPageCount)
                                    }}
                                    isActive={memoriesPage === memoriesPageCount}
                                  >
                                    {memoriesPageCount}
                                  </PaginationLink>
                                </PaginationItem>
                              </>
                            )}

                            <PaginationItem>
                              <PaginationNext
                                href="#"
                                onClick={(e) => {
                                  e.preventDefault()
                                  if (memoriesPage < memoriesPageCount) handlePageChange(memoriesPage + 1)
                                }}
                                className={memoriesPage >= memoriesPageCount ? "pointer-events-none opacity-50" : ""}
                              />
                            </PaginationItem>
                          </PaginationContent>
                        </Pagination>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="episodes" className="mt-6">
              <Card>
                <CardHeader>
                  <CardTitle>Episodes</CardTitle>
                  <CardDescription>Episodes where this user participated</CardDescription>
                </CardHeader>
                <CardContent>
                  {episodesLoading ? (
                    <div className="flex justify-center items-center h-32">
                      <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                    </div>
                  ) : episodes.length === 0 ? (
                    <div className="text-center p-4 bg-muted/40 rounded-md">
                      <p className="text-muted-foreground">No episodes found for this user.</p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {episodes.map((episode) => (
                        <Card key={episode.id} className="overflow-hidden transition-all hover:shadow-md">
                          <CardHeader className="pb-2">
                            <div className="flex items-start justify-between">
                              <div className="flex items-center gap-2">
                                <FlaskConical className="h-4 w-4 text-green-500" />
                                <CardTitle className="text-lg">
                                  Episode {episode.id.split('-')[0]}
                                </CardTitle>
                              </div>
                              <Badge variant={episode.status === 'completed' ? 'default' : 'secondary'}>
                                {episode.status}
                              </Badge>
                            </div>
                            <CardDescription className="flex items-center gap-1">
                              <CalendarDays className="h-3 w-3" />
                              {new Date(episode.created_at).toLocaleDateString()} {new Date(episode.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </CardDescription>
                          </CardHeader>
                          <CardContent>
                            <div className="space-y-3">
                              {episode.scenario_name && (
                                <div>
                                  <span className="text-sm font-medium text-muted-foreground">Scenario: </span>
                                  <span className="text-sm">{episode.scenario_name}</span>
                                </div>
                              )}

                              {episode.role_description && (
                                <div>
                                  <span className="text-sm font-medium text-muted-foreground">Role: </span>
                                  <span className="text-sm">{episode.role_description}</span>
                                </div>
                              )}

                              <div className="flex justify-end gap-2 pt-2">
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() => router.push(`/scenarios/${episode.scenario_id}`)}
                                >
                                  View Scenario
                                </Button>
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() => router.push(`/episodes/${episode.id}`)}
                                >
                                  View Episode
                                </Button>
                              </div>
                            </div>
                          </CardContent>
                        </Card>
                      ))}

                      {episodesPageCount > 1 && (
                        <Pagination className="mt-6">
                          <PaginationContent>
                            <PaginationItem>
                              <PaginationPrevious
                                href="#"
                                onClick={(e) => {
                                  e.preventDefault()
                                  if (episodesPage > 1) handleEpisodesPageChange(episodesPage - 1)
                                }}
                                className={episodesPage <= 1 ? "pointer-events-none opacity-50" : ""}
                              />
                            </PaginationItem>

                            {episodesPageCount <= 7 ? (
                              [...Array(episodesPageCount)].map((_, i) => (
                                <PaginationItem key={i}>
                                  <PaginationLink
                                    href="#"
                                    onClick={(e) => {
                                      e.preventDefault()
                                      handleEpisodesPageChange(i + 1)
                                    }}
                                    isActive={episodesPage === i + 1}
                                  >
                                    {i + 1}
                                  </PaginationLink>
                                </PaginationItem>
                              ))
                            ) : (
                              <>
                                <PaginationItem>
                                  <PaginationLink
                                    href="#"
                                    onClick={(e) => {
                                      e.preventDefault()
                                      handleEpisodesPageChange(1)
                                    }}
                                    isActive={episodesPage === 1}
                                  >
                                    1
                                  </PaginationLink>
                                </PaginationItem>

                                {episodesPage > 3 && (
                                  <PaginationItem>
                                    <div className="flex h-9 w-9 items-center justify-center">
                                      …
                                    </div>
                                  </PaginationItem>
                                )}

                                {Array.from({ length: 3 }, (_, i) => {
                                  const pageNumber = Math.min(
                                    Math.max(episodesPage + i - 1, 2),
                                    episodesPageCount - 1
                                  )

                                  if (pageNumber === 1 || pageNumber === episodesPageCount) {
                                    return null
                                  }

                                  return (
                                    <PaginationItem key={pageNumber}>
                                      <PaginationLink
                                        href="#"
                                        onClick={(e) => {
                                          e.preventDefault()
                                          handleEpisodesPageChange(pageNumber)
                                        }}
                                        isActive={episodesPage === pageNumber}
                                      >
                                        {pageNumber}
                                      </PaginationLink>
                                    </PaginationItem>
                                  )
                                })}

                                {episodesPage < episodesPageCount - 2 && (
                                  <PaginationItem>
                                    <div className="flex h-9 w-9 items-center justify-center">
                                      …
                                    </div>
                                  </PaginationItem>
                                )}

                                <PaginationItem>
                                  <PaginationLink
                                    href="#"
                                    onClick={(e) => {
                                      e.preventDefault()
                                      handleEpisodesPageChange(episodesPageCount)
                                    }}
                                    isActive={episodesPage === episodesPageCount}
                                  >
                                    {episodesPageCount}
                                  </PaginationLink>
                                </PaginationItem>
                              </>
                            )}

                            <PaginationItem>
                              <PaginationNext
                                href="#"
                                onClick={(e) => {
                                  e.preventDefault()
                                  if (episodesPage < episodesPageCount) handleEpisodesPageChange(episodesPage + 1)
                                }}
                                className={episodesPage >= episodesPageCount ? "pointer-events-none opacity-50" : ""}
                              />
                            </PaginationItem>
                          </PaginationContent>
                        </Pagination>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="learning" className="mt-6">
              <Card>
                <CardHeader>
                  <CardTitle>Learning Episodes</CardTitle>
                  <CardDescription>Episodes initiated by this user for learning</CardDescription>
                </CardHeader>
                <CardContent>
                  {learningLoading ? (
                    <div className="flex justify-center items-center h-32">
                      <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                    </div>
                  ) : learningEpisodes.length === 0 ? (
                    <div className="text-center p-4 bg-muted/40 rounded-md">
                      <p className="text-muted-foreground">No learning episodes found for this user.</p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {learningEpisodes.map((episode) => (
                        <Card key={episode.id} className="overflow-hidden transition-all hover:shadow-md border-l-4 border-l-orange-500/50">
                          <CardHeader className="pb-2">
                            <div className="flex items-start justify-between">
                              <div className="flex items-center gap-2">
                                <GraduationCap className="h-4 w-4 text-orange-500" />
                                <CardTitle className="text-lg">
                                  Learning Episode {episode.id.split('-')[0]}
                                </CardTitle>
                              </div>
                              <Badge variant={episode.status === 'completed' ? 'default' : 'secondary'}>
                                {episode.status}
                              </Badge>
                            </div>
                            <CardDescription className="flex items-center gap-1">
                              <CalendarDays className="h-3 w-3" />
                              {new Date(episode.created_at).toLocaleDateString()} {new Date(episode.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </CardDescription>
                          </CardHeader>
                          <CardContent>
                            <div className="space-y-3">
                              {episode.scenario_name && (
                                <div>
                                  <span className="text-sm font-medium text-muted-foreground">Scenario: </span>
                                  <span className="text-sm">{episode.scenario_name}</span>
                                </div>
                              )}

                              {episode.role_description && (
                                <div>
                                  <span className="text-sm font-medium text-muted-foreground">Role: </span>
                                  <span className="text-sm">{episode.role_description}</span>
                                </div>
                              )}

                              <div className="flex items-center gap-2 p-2 bg-orange-50 rounded-md border">
                                <GraduationCap className="h-4 w-4 text-orange-600" />
                                <span className="text-sm text-orange-700 font-medium">Self-initiated Learning Session</span>
                              </div>

                              <div className="flex justify-end gap-2 pt-2">
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() => router.push(`/scenarios/${episode.scenario_id}`)}
                                >
                                  View Scenario
                                </Button>
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() => router.push(`/episodes/${episode.id}`)}
                                >
                                  View Episode
                                </Button>
                              </div>
                            </div>
                          </CardContent>
                        </Card>
                      ))}

                      {learningPageCount > 1 && (
                        <Pagination className="mt-6">
                          <PaginationContent>
                            <PaginationItem>
                              <PaginationPrevious
                                href="#"
                                onClick={(e) => {
                                  e.preventDefault()
                                  if (learningPage > 1) handleLearningPageChange(learningPage - 1)
                                }}
                                className={learningPage <= 1 ? "pointer-events-none opacity-50" : ""}
                              />
                            </PaginationItem>

                            {learningPageCount <= 7 ? (
                              [...Array(learningPageCount)].map((_, i) => (
                                <PaginationItem key={i}>
                                  <PaginationLink
                                    href="#"
                                    onClick={(e) => {
                                      e.preventDefault()
                                      handleLearningPageChange(i + 1)
                                    }}
                                    isActive={learningPage === i + 1}
                                  >
                                    {i + 1}
                                  </PaginationLink>
                                </PaginationItem>
                              ))
                            ) : (
                              <>
                                <PaginationItem>
                                  <PaginationLink
                                    href="#"
                                    onClick={(e) => {
                                      e.preventDefault()
                                      handleLearningPageChange(1)
                                    }}
                                    isActive={learningPage === 1}
                                  >
                                    1
                                  </PaginationLink>
                                </PaginationItem>

                                {learningPage > 3 && (
                                  <PaginationItem>
                                    <div className="flex h-9 w-9 items-center justify-center">
                                      …
                                    </div>
                                  </PaginationItem>
                                )}

                                {Array.from({ length: 3 }, (_, i) => {
                                  const pageNumber = Math.min(
                                    Math.max(learningPage + i - 1, 2),
                                    learningPageCount - 1
                                  )

                                  if (pageNumber === 1 || pageNumber === learningPageCount) {
                                    return null
                                  }

                                  return (
                                    <PaginationItem key={pageNumber}>
                                      <PaginationLink
                                        href="#"
                                        onClick={(e) => {
                                          e.preventDefault()
                                          handleLearningPageChange(pageNumber)
                                        }}
                                        isActive={learningPage === pageNumber}
                                      >
                                        {pageNumber}
                                      </PaginationLink>
                                    </PaginationItem>
                                  )
                                })}

                                {learningPage < learningPageCount - 2 && (
                                  <PaginationItem>
                                    <div className="flex h-9 w-9 items-center justify-center">
                                      …
                                    </div>
                                  </PaginationItem>
                                )}

                                <PaginationItem>
                                  <PaginationLink
                                    href="#"
                                    onClick={(e) => {
                                      e.preventDefault()
                                      handleLearningPageChange(learningPageCount)
                                    }}
                                    isActive={learningPage === learningPageCount}
                                  >
                                    {learningPageCount}
                                  </PaginationLink>
                                </PaginationItem>
                              </>
                            )}

                            <PaginationItem>
                              <PaginationNext
                                href="#"
                                onClick={(e) => {
                                  e.preventDefault()
                                  if (learningPage < learningPageCount) handleLearningPageChange(learningPage + 1)
                                }}
                                className={learningPage >= learningPageCount ? "pointer-events-none opacity-50" : ""}
                              />
                            </PaginationItem>
                          </PaginationContent>
                        </Pagination>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  )
} 