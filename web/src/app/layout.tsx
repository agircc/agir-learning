import type { Metadata } from "next"
import { Inter } from "next/font/google"
import "./globals.css"
import { Navbar } from "@/components/layout/navbar"
import { AuthProvider } from "@/lib/auth-context"

const inter = Inter({ subsets: ["latin"] })

export const metadata: Metadata = {
  title: "Agir Learning",
  description: "Learning from work and reading books",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <AuthProvider>
          <div className="min-h-screen flex flex-col">
            <Navbar />
            <main className="flex-1 px-4 md:px-0">{children}</main>
            <footer className="border-t py-6 bg-background">
              <div className="container mx-auto flex flex-col items-center justify-center gap-4 md:flex-row md:justify-between text-sm text-muted-foreground px-4">
                <div>
                  <p>&copy; {new Date().getFullYear()} Agir Learning. All rights reserved.</p>
                </div>
                <div className="flex items-center gap-4">
                  <a href="#" className="hover:text-foreground transition-colors">Terms</a>
                  <a href="#" className="hover:text-foreground transition-colors">Privacy Policy</a>
                  <a href="#" className="hover:text-foreground transition-colors">Contact</a>
                </div>
              </div>
            </footer>
          </div>
        </AuthProvider>
      </body>
    </html>
  )
}
