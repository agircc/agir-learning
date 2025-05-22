"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { chatAPI } from "@/lib/api"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { ArrowRight, Loader2, MessageSquare } from "lucide-react"

interface Conversation {
  id: string
  name: string
  created_at: string
  related_type: string
  related_id: string
  messages_count: number
}

export default function ChatPage() {
  const router = useRouter()
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchConversations = async () => {
      try {
        setLoading(true)
        const data = await chatAPI.getConversations()
        setConversations(data)
        setError(null)
      } catch (err) {
        console.error("Failed to fetch conversations:", err)
        setError("Failed to load conversations. Please try again later.")
      } finally {
        setLoading(false)
      }
    }

    fetchConversations()
  }, [])

  const handleViewConversation = (id: string) => {
    router.push(`/chat/${id}`)
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return new Intl.DateTimeFormat("en-US", {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(date)
  }

  return (
    <div className="container mx-auto py-10">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold tracking-tight">Chat</h1>
      </div>

      {loading ? (
        <div className="flex justify-center items-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : error ? (
        <div className="rounded-lg border border-destructive bg-destructive/10 p-4">
          <p className="text-destructive">{error}</p>
        </div>
      ) : conversations.length === 0 ? (
        <div className="rounded-lg border border-border p-8 text-center">
          <p className="text-muted-foreground">No conversations found.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {conversations.map((conversation) => (
            <Card key={conversation.id} className="flex flex-col">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <MessageSquare className="h-5 w-5" />
                  {conversation.name}
                </CardTitle>
                <CardDescription>
                  {formatDate(conversation.created_at)}
                </CardDescription>
              </CardHeader>
              <CardContent className="flex-grow">
                <div className="flex flex-col gap-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Messages:</span>
                    <span>{conversation.messages_count}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Type:</span>
                    <span className="capitalize">{conversation.related_type}</span>
                  </div>
                </div>
              </CardContent>
              <div className="p-4 pt-0 mt-auto">
                <Button
                  onClick={() => handleViewConversation(conversation.id)}
                  className="w-full"
                >
                  View Conversation
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
} 