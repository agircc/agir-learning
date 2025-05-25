"use client"

import { useEffect, useState } from "react"
import { useRouter, useParams } from "next/navigation"
import { scenariosAPI } from "@/lib/api"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Loader2, ArrowLeft, ArrowRight, ArrowDownRight } from "lucide-react"
import Link from "next/link"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

interface ScenarioState {
  id: string
  name: string
  description: string
  data: Record<string, unknown>
  roles: { id: string; name: string; agent_role: string }[]
  transitions_from: { id: string; description: string; to_state_id: string; to_state_name: string }[]
  transitions_to: { id: string; description: string; from_state_id: string; from_state_name: string }[]
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

// Component for the state flow diagram
const StateFlowDiagram = ({ states }: { states: ScenarioState[] }) => {
  // Find starting states (states with no incoming transitions)
  const startingStates = states.filter(state => state.transitions_to.length === 0)

  // Find ending states (states with no outgoing transitions)
  const endingStates = states.filter(state => state.transitions_from.length === 0)

  return (
    <div className="w-full overflow-x-auto">
      <div className="min-w-fit p-4">
        {/* Starting states */}
        {startingStates.length > 0 && (
          <div className="mb-6">
            <h4 className="text-sm font-medium mb-3 text-green-700">Starting States</h4>
            <div className="flex flex-wrap gap-4">
              {startingStates.map(state => (
                <div key={state.id} className="relative">
                  <Card className="bg-green-50 border-green-200 min-w-[200px]">
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium text-green-800">{state.name}</CardTitle>
                    </CardHeader>
                    <CardContent className="pt-0">
                      <p className="text-xs text-green-700">{state.description || "No description"}</p>
                      {state.roles.length > 0 && (
                        <div className="mt-2">
                          <p className="text-xs font-medium text-green-600">Roles:</p>
                          <div className="text-xs text-green-500 ml-2">
                            {state.roles.map((role) => (
                              <div key={role.id}>
                                {role.name} ({role.agent_role})
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </CardContent>
                  </Card>

                  {/* Outgoing transitions */}
                  {state.transitions_from.map(transition => (
                    <div key={transition.id} className="flex items-center mt-2 ml-4">
                      <ArrowDownRight className="h-4 w-4 text-muted-foreground mr-2" />
                      <span className="text-xs text-muted-foreground bg-muted px-2 py-1 rounded">
                        {transition.description}
                      </span>
                      <ArrowRight className="h-4 w-4 text-muted-foreground mx-2" />
                      <span className="text-xs font-medium">{transition.to_state_name}</span>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Middle states (have both incoming and outgoing transitions) */}
        {states.filter(state => state.transitions_to.length > 0 && state.transitions_from.length > 0).length > 0 && (
          <div className="mb-6">
            <h4 className="text-sm font-medium mb-3 text-blue-700">Intermediate States</h4>
            <div className="flex flex-wrap gap-4">
              {states
                .filter(state => state.transitions_to.length > 0 && state.transitions_from.length > 0)
                .map(state => (
                  <div key={state.id} className="relative">
                    <Card className="bg-blue-50 border-blue-200 min-w-[200px]">
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-blue-800">{state.name}</CardTitle>
                      </CardHeader>
                      <CardContent className="pt-0">
                        <p className="text-xs text-blue-700">{state.description || "No description"}</p>
                        {state.roles.length > 0 && (
                          <div className="mt-2">
                            <p className="text-xs font-medium text-blue-600">Roles:</p>
                            <div className="text-xs text-blue-500 ml-2">
                              {state.roles.map((role) => (
                                <div key={role.id}>
                                  {role.name} ({role.agent_role})
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Incoming transitions */}
                        <div className="mt-2">
                          <p className="text-xs font-medium text-blue-600">From:</p>
                          {state.transitions_to.map(transition => (
                            <div key={transition.id} className="text-xs text-blue-500 ml-2">
                              {transition.from_state_name}
                            </div>
                          ))}
                        </div>
                      </CardContent>
                    </Card>

                    {/* Outgoing transitions */}
                    {state.transitions_from.map(transition => (
                      <div key={transition.id} className="flex items-center mt-2 ml-4">
                        <ArrowDownRight className="h-4 w-4 text-muted-foreground mr-2" />
                        <span className="text-xs text-muted-foreground bg-muted px-2 py-1 rounded">
                          {transition.description}
                        </span>
                        <ArrowRight className="h-4 w-4 text-muted-foreground mx-2" />
                        <span className="text-xs font-medium">{transition.to_state_name}</span>
                      </div>
                    ))}
                  </div>
                ))}
            </div>
          </div>
        )}

        {/* Ending states */}
        {endingStates.length > 0 && (
          <div className="mb-6">
            <h4 className="text-sm font-medium mb-3 text-red-700">Ending States</h4>
            <div className="flex flex-wrap gap-4">
              {endingStates.map(state => (
                <div key={state.id} className="relative">
                  <Card className="bg-red-50 border-red-200 min-w-[200px]">
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium text-red-800">{state.name}</CardTitle>
                    </CardHeader>
                    <CardContent className="pt-0">
                      <p className="text-xs text-red-700">{state.description || "No description"}</p>
                      {state.roles.length > 0 && (
                        <div className="mt-2">
                          <p className="text-xs font-medium text-red-600">Roles:</p>
                          <div className="text-xs text-red-500 ml-2">
                            {state.roles.map((role) => (
                              <div key={role.id}>
                                {role.name} ({role.agent_role})
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Incoming transitions */}
                      {state.transitions_to.length > 0 && (
                        <div className="mt-2">
                          <p className="text-xs font-medium text-red-600">From:</p>
                          {state.transitions_to.map(transition => (
                            <div key={transition.id} className="text-xs text-red-500 ml-2">
                              {transition.from_state_name}
                            </div>
                          ))}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Show states that have no transitions at all (isolated states) */}
        {states.filter(state => state.transitions_to.length === 0 && state.transitions_from.length === 0).length > 0 && (
          <div className="mb-6">
            <h4 className="text-sm font-medium mb-3 text-gray-700">Isolated States</h4>
            <div className="flex flex-wrap gap-4">
              {states
                .filter(state => state.transitions_to.length === 0 && state.transitions_from.length === 0)
                .map(state => (
                  <Card key={state.id} className="bg-gray-50 border-gray-200 min-w-[200px]">
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium text-gray-800">{state.name}</CardTitle>
                    </CardHeader>
                    <CardContent className="pt-0">
                      <p className="text-xs text-gray-700">{state.description || "No description"}</p>
                      {state.roles.length > 0 && (
                        <div className="mt-2">
                          <p className="text-xs font-medium text-gray-600">Roles:</p>
                          <div className="text-xs text-gray-500 ml-2">
                            {state.roles.map((role) => (
                              <div key={role.id}>
                                {role.name} ({role.agent_role})
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default function ScenarioDetailsPage() {
  const router = useRouter()
  const params = useParams()
  const id = params.id as string
  const [scenario, setScenario] = useState<Scenario | null>(null)
  const [episodes, setEpisodes] = useState<Episode[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchScenarioData = async () => {
      try {
        setLoading(true)
        const scenarioData = await scenariosAPI.getById(id)
        setScenario(scenarioData)

        const episodesData = await scenariosAPI.getEpisodes(id)

        // Sort episodes by created_at in descending order (newest first) for additional safety
        const sortedEpisodes = [...episodesData].sort((a, b) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        )

        setEpisodes(sortedEpisodes)

        setError(null)
      } catch (err) {
        console.error("Failed to fetch scenario data:", err)
        setError("Failed to load scenario details. Please try again later.")
      } finally {
        setLoading(false)
      }
    }

    if (id) {
      fetchScenarioData()
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

  if (!scenario) {
    return (
      <div className="container mx-auto py-10">
        <div className="rounded-lg border border-border p-8 text-center">
          <p className="text-muted-foreground">Scenario not found.</p>
        </div>
      </div>
    )
  }

  return (
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

            <Tabs defaultValue="flow" className="mt-6">
              <TabsList>
                <TabsTrigger value="flow">State Flow</TabsTrigger>
                <TabsTrigger value="details">State Details</TabsTrigger>
                <TabsTrigger value="episodes">Episodes ({episodes.length})</TabsTrigger>
              </TabsList>

              <TabsContent value="flow" className="mt-4">
                <Card>
                  <CardHeader>
                    <CardTitle>State Transition Flow</CardTitle>
                    <CardDescription>Visual representation of how states transition to each other</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <StateFlowDiagram states={scenario.states} />
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="details" className="space-y-4 mt-4">
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
                          <div className="mb-3">
                            <h4 className="text-sm font-medium mb-1">Transitions To:</h4>
                            <ul className="text-sm list-disc pl-5">
                              {state.transitions_from.map((transition) => (
                                <li key={transition.id}>
                                  {transition.description} → {transition.to_state_name}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {state.transitions_to.length > 0 && (
                          <div>
                            <h4 className="text-sm font-medium mb-1">Transitions From:</h4>
                            <ul className="text-sm list-disc pl-5">
                              {state.transitions_to.map((transition) => (
                                <li key={transition.id}>
                                  {transition.from_state_name} → {state.name}
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
  )
} 