"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { scenariosAPI } from "@/lib/api"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Loader2, ArrowLeft, ArrowRight } from "lucide-react"
import Link from "next/link"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ProtectedRoute } from "@/components/auth/protected-route"

interface ScenarioState {
  id: string
  name: string
  description: string
  data: any
  roles: { id: string; name: string; agent_role: string }[]
  transitions_from: { id: string; name: string; to_state_id: string; to_state_name: string }[]
  transitions_to: { id: string; name: string; from_state_id: string; from_state_name: string }[]
}

interface Scenario {
  id: string
  name: string
  description: string
  created_at: string
  updated_at: string
  states: ScenarioState[]
  episodes_count: number
}

interface Episode {
  id: string
  scenario_id: string
  status: string
  created_at: string
}

export default function ScenarioDetailsPage({ params }: { params: { id: string } }) {
  const router = useRouter()
  const [scenario, setScenario] = useState<Scenario | null>(null)
  const [episodes, setEpisodes] = useState<Episode[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchScenarioData = async () => {
      try {
        setLoading(true)
        const scenarioData = await scenariosAPI.getById(params.id)
        setScenario(scenarioData)

        const episodesData = await scenariosAPI.getEpisodes(params.id)
        setEpisodes(episodesData)

        setError(null)
      } catch (err) {
        console.error("Failed to fetch scenario data:", err)
        setError("Failed to load scenario details. Please try again later.")
      } finally {
        setLoading(false)
      }
    }

    fetchScenarioData()
  }, [params.id])

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

  if (!scenario) {
    return (
      <ProtectedRoute>
        <div className="container mx-auto py-10">
          <div className="rounded-lg border border-border p-8 text-center">
            <p className="text-muted-foreground">Scenario not found.</p>
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
            <Link href="/scenarios">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Scenarios
            </Link>
          </Button>
        </div>

        <div className="grid grid-cols-1 gap-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-2xl">{scenario.name}</CardTitle>
              <CardDescription>
                Created: {new Date(scenario.created_at).toLocaleDateString()}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="mb-4">{scenario.description || "No description available"}</p>

              <Tabs defaultValue="states" className="mt-6">
                <TabsList>
                  <TabsTrigger value="states">States</TabsTrigger>
                  <TabsTrigger value="episodes">Episodes ({episodes.length})</TabsTrigger>
                </TabsList>

                <TabsContent value="states" className="space-y-4 mt-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {scenario.states.map((state) => (
                      <Card key={state.id} className="bg-muted/40">
                        <CardHeader className="pb-2">
                          <CardTitle className="text-lg">{state.name}</CardTitle>
                        </CardHeader>
                        <CardContent>
                          <p className="text-sm mb-3">{state.description || "No description available"}</p>

                          {state.roles.length > 0 && (
                            <div className="mb-3">
                              <h4 className="text-sm font-medium mb-1">Roles:</h4>
                              <ul className="text-sm list-disc pl-5">
                                {state.roles.map((role) => (
                                  <li key={role.id}>{role.name} ({role.agent_role})</li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {state.transitions_from.length > 0 && (
                            <div>
                              <h4 className="text-sm font-medium mb-1">Transitions:</h4>
                              <ul className="text-sm list-disc pl-5">
                                {state.transitions_from.map((transition) => (
                                  <li key={transition.id}>
                                    {transition.name} → {transition.to_state_name}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </TabsContent>

                <TabsContent value="episodes" className="space-y-4 mt-4">
                  {episodes.length === 0 ? (
                    <div className="text-center p-4 bg-muted/40 rounded-md">
                      <p className="text-muted-foreground">No episodes available for this scenario.</p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {episodes.map((episode) => (
                        <Card key={episode.id} className="bg-muted/40">
                          <CardHeader className="pb-2">
                            <CardTitle className="text-lg flex justify-between items-center">
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
                            <div className="flex justify-end">
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => router.push(`/episodes/${episode.id}`)}
                              >
                                View Details
                                <ArrowRight className="ml-2 h-4 w-4" />
                              </Button>
                            </div>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  )}
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        </div>
      </div>
    </ProtectedRoute>
  )
} 