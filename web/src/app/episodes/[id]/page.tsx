"use client"

import { useEffect, useState } from "react"
import { useRouter, useParams } from "next/navigation"
import { episodesAPI, stepsAPI } from "@/lib/api"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Loader2, ArrowLeft, ChevronRight, MessageSquare } from "lucide-react"
import Link from "next/link"

interface Step {
  id: string
  action: string
  state_id: string
  created_at: string
  updated_at: string
  generated_text?: string
  state?: {
    id: string
    name: string
    description: string
  }
  conversations_count?: number
}

interface Episode {
  id: string
  scenario_id: string
  status: string
  created_at: string
  updated_at: string
}

export default function EpisodeDetailsPage() {
  const router = useRouter()
  const params = useParams()
  const id = params.id as string
  const [episode, setEpisode] = useState<Episode | null>(null)
  const [steps, setSteps] = useState<Step[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchEpisodeData = async () => {
      try {
        setLoading(true)
        const episodeData = await episodesAPI.getById(id)
        setEpisode(episodeData)

        const stepsData = await episodesAPI.getSteps(id)

        // Get detailed information for each step
        const detailedSteps = await Promise.all(
          stepsData.map(async (step: Step) => {
            try {
              const stepDetails = await stepsAPI.getDetails(step.id)
              const conversations = await stepsAPI.getConversations(step.id)
              return {
                ...step,
                generated_text: stepDetails.generated_text,
                state: stepDetails.state,
                conversations_count: conversations.length
              }
            } catch (err) {
              console.error(`Failed to fetch details for step ${step.id}:`, err)
              return step // Return original step if details fail
            }
          })
        )

        setSteps(detailedSteps)

        setError(null)
      } catch (err) {
        console.error("Failed to fetch episode data:", err)
        setError("Failed to load episode details. Please try again later.")
      } finally {
        setLoading(false)
      }
    }

    if (id) {
      fetchEpisodeData()
    }
  }, [id])

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

  if (!episode) {
    return (
      <div className="container mx-auto py-10">
        <div className="rounded-lg border border-border p-8 text-center">
          <p className="text-muted-foreground">Episode not found.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto py-10">
      <div className="mb-6">
        <Button variant="outline" size="sm" asChild>
          <Link href={`/scenarios/${episode.scenario_id}`}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Scenario
          </Link>
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-2xl flex justify-between items-center">
              <span>Episode {episode.id.split('-')[0]}</span>
              <span className="text-sm px-2 py-1 bg-primary/10 text-primary rounded-md">
                {episode.status}
              </span>
            </CardTitle>
            <CardDescription>
              Created: {new Date(episode.created_at).toLocaleDateString()}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <h3 className="text-lg font-medium mb-4">Steps</h3>
            {steps.length === 0 ? (
              <div className="text-center p-4 bg-muted/40 rounded-md">
                <p className="text-muted-foreground">No steps available for this episode.</p>
              </div>
            ) : (
              <div className="space-y-4">
                {steps.map((step, index) => (
                  <Card key={step.id} className="bg-muted/40">
                    <CardHeader className="pb-2">
                      <CardTitle className="text-lg flex justify-between items-center">
                        <span>Step {index + 1}</span>
                        {step.state && (
                          <span className="text-sm px-2 py-1 bg-primary/10 text-primary rounded-md">
                            {step.state.name}
                          </span>
                        )}
                      </CardTitle>
                      <CardDescription>
                        Created: {new Date(step.created_at).toLocaleDateString()}
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      {step.generated_text && (
                        <div className="mb-4">
                          <h4 className="text-sm font-medium mb-2">Generated Content:</h4>
                          <p className="text-sm p-3 bg-background rounded-md border leading-relaxed">
                            {step.generated_text}
                          </p>
                        </div>
                      )}

                      {step.state?.description && (
                        <div className="mb-4">
                          <h4 className="text-sm font-medium mb-2">State Description:</h4>
                          <p className="text-sm text-muted-foreground">
                            {step.state.description}
                          </p>
                        </div>
                      )}

                      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-2">
                        {step.conversations_count && step.conversations_count > 0 && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => router.push(`/steps/${step.id}#conversations`)}
                            className="w-full sm:w-auto"
                          >
                            <MessageSquare className="mr-2 h-4 w-4" />
                            <span className="hidden sm:inline">View Conversations ({step.conversations_count})</span>
                            <span className="sm:hidden">Conversations ({step.conversations_count})</span>
                          </Button>
                        )}
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => router.push(`/steps/${step.id}`)}
                          className="w-full sm:w-auto sm:ml-auto"
                        >
                          <span className="hidden sm:inline">View Details</span>
                          <span className="sm:hidden">Details</span>
                          <ChevronRight className="ml-2 h-4 w-4" />
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
} 