import Link from "next/link"
import { ArrowRight, LayoutDashboard, Users, MessageSquare } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card"

export default function Home() {
  return (
    <div className="container mx-auto py-10">
      <div className="text-center mb-10">
        <h1 className="text-4xl font-bold tracking-tight">Agir Learning</h1>
        <p className="mt-4 text-lg text-muted-foreground">
          Explore scenarios, interact with users, and visualize the simulation
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Scenarios Card */}
        <Card className="flex flex-col">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <LayoutDashboard className="h-5 w-5" />
              Scenarios
            </CardTitle>
            <CardDescription>
              Browse and analyze scenarios, episodes, and steps
            </CardDescription>
          </CardHeader>
          <CardContent className="flex-grow">
            <p>
              View the progression of scenarios through episodes and individual steps.
              Explore conversations and interactions within each step.
            </p>
          </CardContent>
          <CardFooter>
            <Link href="/scenarios" className="w-full">
              <Button className="w-full">
                View Scenarios
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </Link>
          </CardFooter>
        </Card>

        {/* Users Card */}
        <Card className="flex flex-col">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Users className="h-5 w-5" />
              Users
            </CardTitle>
            <CardDescription>
              Browse users and their memories
            </CardDescription>
          </CardHeader>
          <CardContent className="flex-grow">
            <p>
              View user profiles, explore their memories, and understand their knowledge.
              Filter memories by type and importance.
            </p>
          </CardContent>
          <CardFooter>
            <Link href="/users" className="w-full">
              <Button className="w-full">
                View Users
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </Link>
          </CardFooter>
        </Card>

        {/* Chat Card */}
        <Card className="flex flex-col">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <MessageSquare className="h-5 w-5" />
              Chat
            </CardTitle>
            <CardDescription>
              Chat with users and view conversations
            </CardDescription>
          </CardHeader>
          <CardContent className="flex-grow">
            <p>
              Interact with users through chat, review existing conversations,
              and analyze communication patterns.
            </p>
          </CardContent>
          <CardFooter>
            <Link href="/chat" className="w-full">
              <Button className="w-full">
                Go to Chat
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </Link>
          </CardFooter>
        </Card>
      </div>
    </div>
  )
}
