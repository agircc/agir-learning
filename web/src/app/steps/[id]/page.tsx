"use client"

import { useEffect, useState } from "react"
import { useParams } from "next/navigation"
import { stepsAPI } from "@/lib/api"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Loader2, ArrowLeft } from "lucide-react"
import Link from "next/link"

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
  generated_text: string
  state: State
}

export default function StepDetailsPage() {
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

        // Sort messages within each conversation by created_at for additional safety
        const sortedConversations = conversationsData.map((conv: Conversation) => ({
          ...conv,
          messages: [...conv.messages].sort((a, b) =>
            new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
          )
        }))

        setConversations(sortedConversations)

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

  // Handle URL hash navigation to conversations
  useEffect(() => {
    if (typeof window !== 'undefined' && window.location.hash === '#conversations') {
      // Wait for the component to render and scroll to conversations
      setTimeout(() => {
        const conversationsElement = document.getElementById('conversations-section')
        if (conversationsElement) {
          conversationsElement.scrollIntoView({ behavior: 'smooth' })
        }
      }, 100)
    }
  }, [conversations])

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

  if (!step) {
    return (
      <div className="container mx-auto py-10">
        <div className="rounded-lg border border-border p-8 text-center">
          <p className="text-muted-foreground">Step not found.</p>
        </div>
      </div>
    )
  }

  return (
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
              <h3 className="text-lg font-medium mb-2">Generated Text</h3>
              <p className="p-3 bg-muted rounded-md">{step.generated_text}</p>
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
              <div id="conversations-section">
                <h3 className="text-lg font-medium mb-4">Conversations</h3>
                <div className="space-y-6">
                  {conversations.map((conv) => (
                    <div key={conv.id} className="space-y-4">
                      {conversations.length > 1 && (
                        <h4 className="text-md font-medium text-muted-foreground border-b pb-2">
                          {conv.name}
                        </h4>
                      )}
                      <div className="space-y-4">
                        {conv.messages.map((message) => (
                          <div
                            key={message.id}
                            className="p-3 bg-muted rounded-md"
                          >
                            <div className="mb-1 flex flex-col sm:flex-row sm:justify-between sm:items-center gap-1">
                              <span className="font-medium">{message.sender_name}</span>
                              <span className="text-xs text-muted-foreground">
                                {new Date(message.created_at).toLocaleString()}
                              </span>
                            </div>
                            <p>{message.content}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}