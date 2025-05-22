"use client"

import { useEffect, useState, useRef } from "react"
import { useParams, useRouter } from "next/navigation"
import { usersAPI, chatAPI } from "@/lib/api"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Loader2, ArrowLeft, Send } from "lucide-react"
import Link from "next/link"
import { ProtectedRoute } from "@/components/auth/protected-route"
import { Textarea } from "@/components/ui/textarea"
import { ScrollArea } from "@/components/ui/scroll-area"

interface User {
  id: string
  username: string
  full_name: string
  avatar?: string
}

interface Message {
  id: string
  content: string
  sender_id: string
  sender_name: string
  created_at: string
}

interface Conversation {
  id: string
  name: string
  created_at: string
  related_type: string
  related_id: string
  messages: Message[]
}

export default function ChatPage() {
  const router = useRouter()
  const params = useParams()
  const userId = params.userId as string
  const [user, setUser] = useState<User | null>(null)
  const [conversation, setConversation] = useState<Conversation | null>(null)
  const [message, setMessage] = useState("")
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    if (conversation?.messages) {
      scrollToBottom()
    }
  }, [conversation?.messages])

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true)
        // Get user info
        const userData = await usersAPI.getById(userId)
        setUser(userData)

        // Try to find existing conversation with this user
        try {
          const conversations = await chatAPI.getConversations()
          const userConversation = conversations.find(
            (conv: any) => conv.related_type === "user" && conv.related_id === userId
          )

          if (userConversation) {
            const conversationData = await chatAPI.getConversationById(userConversation.id)
            setConversation(conversationData)
          }
        } catch (convErr) {
          console.error("Failed to fetch conversations, will create new one:", convErr)
        }

        setError(null)
      } catch (err) {
        console.error("Failed to fetch user data:", err)
        setError("Failed to load user or conversation. Please try again later.")
      } finally {
        setLoading(false)
      }
    }

    if (userId) {
      fetchData()
    }
  }, [userId])

  const handleSendMessage = async () => {
    if (!message.trim() || !user || sending) return

    try {
      setSending(true)
      const response = await chatAPI.sendToUser(
        userId,
        message,
        conversation?.id
      )

      // Clear the input
      setMessage("")

      // Refresh conversation to get latest messages
      if (response.conversation_id) {
        const updatedConversation = await chatAPI.getConversationById(response.conversation_id)
        setConversation(updatedConversation)
      }
    } catch (err) {
      console.error("Failed to send message:", err)
      setError("Failed to send message. Please try again.")
    } finally {
      setSending(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
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
            <Link href={`/users/${userId}`}>
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to User
            </Link>
          </Button>
        </div>

        <Card className="max-w-3xl mx-auto">
          <CardHeader>
            <CardTitle className="text-xl">
              Chat with {user.full_name || user.username}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col h-[60vh]">
              <ScrollArea className="flex-1 p-4 mb-4 border rounded-md">
                {!conversation || conversation.messages.length === 0 ? (
                  <div className="flex items-center justify-center h-full text-muted-foreground">
                    No messages yet. Start the conversation!
                  </div>
                ) : (
                  <div className="space-y-4">
                    {conversation.messages.map((msg) => (
                      <div
                        key={msg.id}
                        className={`flex ${msg.sender_id !== userId ? "justify-end" : "justify-start"
                          }`}
                      >
                        <div
                          className={`max-w-[80%] rounded-lg px-4 py-2 ${msg.sender_id !== userId
                              ? "bg-primary text-primary-foreground"
                              : "bg-muted"
                            }`}
                        >
                          <div className="text-xs mb-1">
                            {msg.sender_name || "Unknown"} • {new Date(msg.created_at).toLocaleTimeString()}
                          </div>
                          <div className="whitespace-pre-wrap">{msg.content}</div>
                        </div>
                      </div>
                    ))}
                    <div ref={messagesEndRef} />
                  </div>
                )}
              </ScrollArea>

              <div className="flex gap-2">
                <Textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Type your message..."
                  className="flex-1 resize-none"
                  rows={2}
                />
                <Button
                  onClick={handleSendMessage}
                  disabled={sending || !message.trim()}
                  className="self-end"
                >
                  {sending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Send className="h-4 w-4" />
                  )}
                  <span className="ml-2">Send</span>
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </ProtectedRoute>
  )
} 