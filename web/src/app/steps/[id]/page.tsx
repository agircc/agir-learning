"use client"

import { useEffect, useState } from "react"
import { useRouter, useParams } from "next/navigation"
import { stepsAPI } from "@/lib/api"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Loader2, ArrowLeft } from "lucide-react"
import Link from "next/link"
import { ProtectedRoute } from "@/components/auth/protected-route"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

interface State {
  id: string
  name: string
  description: string
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
  messages: Message[]
}

interface StepDetails {
  id: string
  action: string
  created_at: string
  updated_at: string
  episode_id: string
  state_id: string
  state: State
}

export default function StepDetailsPage() {
  const router = useRouter()
  const params = useParams()
  const id = params.id as string
  const [step, setStep] = useState<StepDetails | null>(null)
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchStepData = async () => {
      try {
        setLoading(true)
        const stepData = await stepsAPI.getDetails(id)
        setStep(stepData)

        const conversationsData = await stepsAPI.getConversations(id)
        setConversations(conversationsData)

        setError(null)
      } catch (err) {
        console.error("Failed to fetch step data:", err)
        setError("Failed to load step details. Please try again later.")
      } finally {
        setLoading(false)
      }
    }

    if (id) {
      fetchStepData()
    }
  }, [id])

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

  if (!step) {
    return (
      <ProtectedRoute>
        <div className="container mx-auto py-10">
          <div className="rounded-lg border border-border p-8 text-center">
            <p className="text-muted-foreground">Step not found.</p>
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
            <Link href={`/episodes/${step.episode_id}`}>
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Episode
            </Link>
          </Button>
        </div>

        <div className="grid grid-cols-1 gap-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-2xl">Step Details</CardTitle>
              <CardDescription>
                Created: {new Date(step.created_at).toLocaleDateString()}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="mb-6">
                <h3 className="text-lg font-medium mb-2">Action</h3>
                <p className="p-3 bg-muted rounded-md">{step.action}</p>
              </div>

              <div className="mb-6">
                <h3 className="text-lg font-medium mb-2">State</h3>
                <Card className="bg-muted/40">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-md">{step.state.name}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p>{step.state.description || "No description available"}</p>
                  </CardContent>
                </Card>
              </div>

              {conversations.length > 0 && (
                <div>
                  <h3 className="text-lg font-medium mb-4">Conversations</h3>
                  <Tabs defaultValue={conversations[0].id}>
                    <TabsList className="mb-4">
                      {conversations.map((conv) => (
                        <TabsTrigger key={conv.id} value={conv.id}>
                          {conv.name}
                        </TabsTrigger>
                      ))}
                    </TabsList>

                    {conversations.map((conv) => (
                      <TabsContent key={conv.id} value={conv.id} className="space-y-4">
                        <div className="space-y-4">
                          {conv.messages.map((message) => (
                            <div
                              key={message.id}
                              className="p-3 bg-muted rounded-md"
                            >
                              <div className="mb-1 flex justify-between">
                                <span className="font-medium">{message.sender_name}</span>
                                <span className="text-xs text-muted-foreground">
                                  {new Date(message.created_at).toLocaleString()}
                                </span>
                              </div>
                              <p>{message.content}</p>
                            </div>
                          ))}
                        </div>
                      </TabsContent>
                    ))}
                  </Tabs>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </ProtectedRoute>
  )
} 