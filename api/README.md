# AGIR API

This directory contains a FastAPI implementation of the AGIR Visualization API.

## Features

- RESTful API for accessing all AGIR data:
  - Scenarios
  - Episodes
  - Steps
  - Users
  - Memories
  - Chat functionality
- Built with FastAPI for high performance and automatic API documentation
- Direct integration with AGIR database models

## Getting Started

### Prerequisites

- Python 3.8+
- Access to AGIR database (configured via environment variables)

### Running the API

1. Make sure you have the required environment variables set (or use a `.env` file)
   ```
   SQLALCHEMY_DATABASE_URI=postgresql://user:password@localhost:5432/agir
   API_PORT=8000  # optional, defaults to 8000
   ```

2. Run the API server:
   ```bash
   python -m api.run
   ```

3. Access the API documentation:
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## API Endpoints

The API provides the following endpoints:

- `/api/scenarios` - Access scenario data
- `/api/episodes` - Access episode data
- `/api/steps` - Access step data
- `/api/users` - Access user data
- `/api/memories` - Access memory data
- `/api/chat` - Chat functionality

See the API documentation for detailed information about all available endpoints.