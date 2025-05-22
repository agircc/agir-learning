"use client"

import { useEffect, useState } from "react"
import { useRouter, useParams } from "next/navigation"
import { episodesAPI } from "@/lib/api"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Loader2, ArrowLeft, ChevronRight } from "lucide-react"
import Link from "next/link"
import { ProtectedRoute } from "@/components/auth/protected-route"

interface Step {
  id: string
  action: string
  state_id: string
  created_at: string
  updated_at: string
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
        setSteps(stepsData)

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

  if (!episode) {
    return (
      <ProtectedRoute>
        <div className="container mx-auto py-10">
          <div className="rounded-lg border border-border p-8 text-center">
            <p className="text-muted-foreground">Episode not found.</p>
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
                        <CardTitle className="text-lg">Step {index + 1}</CardTitle>
                        <CardDescription>
                          Created: {new Date(step.created_at).toLocaleDateString()}
                        </CardDescription>
                      </CardHeader>
                      <CardContent>
                        <p className="mb-3"><strong>Action:</strong> {step.action}</p>
                        <div className="flex justify-end">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => router.push(`/steps/${step.id}`)}
                          >
                            View Details
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
    </ProtectedRoute>
  )
} 