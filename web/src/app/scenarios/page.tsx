"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { scenariosAPI } from "@/lib/api"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { ArrowRight, Loader2 } from "lucide-react"
import { ProtectedRoute } from "@/components/auth/protected-route"

interface Scenario {
  id: string
  name: string
  description: string
  created_at: string
}

export default function ScenariosPage() {
  const router = useRouter()
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchScenarios = async () => {
      try {
        setLoading(true)
        const data = await scenariosAPI.getAll()
        setScenarios(data)
        setError(null)
      } catch (err) {
        console.error("Failed to fetch scenarios:", err)
        setError("Failed to load scenarios. Please try again later.")
      } finally {
        setLoading(false)
      }
    }

    fetchScenarios()
  }, [])

  const handleViewScenario = (id: string) => {
    router.push(`/scenarios/${id}`)
  }

  return (
    <ProtectedRoute>
      <div className="container mx-auto py-10">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold tracking-tight">Scenarios</h1>
        </div>

        {loading ? (
          <div className="flex justify-center items-center h-64">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : error ? (
          <div className="rounded-lg border border-destructive bg-destructive/10 p-4">
            <p className="text-destructive">{error}</p>
          </div>
        ) : scenarios.length === 0 ? (
          <div className="rounded-lg border border-border p-8 text-center">
            <p className="text-muted-foreground">No scenarios found.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {scenarios.map((scenario) => (
              <Card key={scenario.id} className="flex flex-col">
                <CardHeader>
                  <CardTitle>{scenario.name}</CardTitle>
                  <CardDescription>
                    Created: {new Date(scenario.created_at).toLocaleDateString()}
                  </CardDescription>
                </CardHeader>
                <CardContent className="flex-grow">
                  <p className="text-sm text-muted-foreground">
                    {scenario.description || "No description available"}
                  </p>
                </CardContent>
                <div className="p-4 pt-0 mt-auto">
                  <Button
                    onClick={() => handleViewScenario(scenario.id)}
                    className="w-full"
                  >
                    View Details
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </ProtectedRoute>
  )
} 