# AGIR Web Visualization

This directory contains a Next.js implementation of the AGIR Visualization web interface.

## Features

- Modern web interface for accessing AGIR data:
  - Scenarios, episodes, and steps visualization
  - User management and memory exploration
  - Chat functionality
- Built with:
  - Next.js 14 for server-side rendering and routing
  - TailwindCSS for styling
  - shadcn/ui components for a consistent UI
  - Lucide React for icons
  - TypeScript for type safety

## Getting Started

### Prerequisites

- Node.js 18.17 or later
- AGIR API running (defaults to http://localhost:8000)

### Installation

1. Install dependencies:
   ```bash
   npm install
   ```

### Development

1. Set up environment variables (create a `.env.local` file):
   ```
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

2. Start the development server:
   ```bash
   npm run dev
   ```

3. Open [http://localhost:3000](http://localhost:3000) with your browser to see the application.

### Building for Production

1. Build the application:
   ```bash
   npm run build
   ```

2. Start the production server:
   ```bash
   npm start
   ```

## Project Structure

- `src/app` - Next.js pages and layouts
- `src/components` - Reusable UI components
- `src/lib` - Utility functions and API client
- `public` - Static assets

## Features

### Scenarios Page
- View all scenarios
- Click on a scenario to see its episodes and steps

### Users Page
- View all users
- See user details and memories
- Filter users by search term

### Chat Page
- View all conversations
- Chat with users
- View conversation history
