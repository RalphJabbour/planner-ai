# Planner AI

Planner AI is a comprehensive academic planning and course management system designed to help students organize their educational journey. The application features course synchronization, behavior analysis, interactive quizzes, and personalized planning tools, including an AI chat assistant.

## 🚀 Features

- **Course Management**: Track and manage academic courses
- **Intelligent Planning**: AI-powered planning suggestions via chat
- **Interactive Quizzes**: We assess your knowledge through our IEP
- **Behavior Analysis**: Study pattern and behavior tracking
- **Course Synchronization**: Automatic synchronization with academic databases

## 🛠️ Tech Stack

### Frontend
- React 19
- Vite
- TailwindCSS
- React Router

### Backend
- FastAPI
- SQLAlchemy
- PostgreSQL
- Python 3.12+

### Services
- **Frontend**: React UI served via Nginx
- **Backend**: Core FastAPI application, handles authentication, main API logic.
- **MCP Server**: Exposes database operations as tools for the AI.
- **MCP Client**: Connects Backend chat to OpenAI and MCP Server tools.
- **Behavior Analyzer**: ML-powered analysis of student behavior.
- **Course Sync**: Automated course data synchronization.
- **IEP Quiz**: Interactive quiz system.
- **Database**: PostgreSQL data storage.

## 🏗️ Architecture

The application is built using a microservices architecture with Docker, allowing each component to scale independently. Key components include the Frontend, Backend, Database, and specialized services like the MCP Server/Client for AI interaction, Behavior Analyzer, Course Sync, and IEP Quiz.

## 🚀 Getting Started

### Prerequisites

- Docker and Docker Compose
- Git

### Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/yourusername/planner-ai.git # Replace with your repo URL
    cd planner-ai
    ```

2.  Create environment files:
    - Create `.env` in the root directory (for Docker Compose)
    - Create `backend/.env`
    - Create `mcp_client/.env` (for Azure OpenAI credentials)
    - Create `iep-quiz/.env`
    - Create `behavior_analyzer/.env`
    
    **Example `.env` (root directory):**
    ```
    DATABASE_URL=postgresql://postgres:1234@db:5432/EECE503N-planner
    POSTGRES_PASSWORD=1234
    POSTGRES_USER=postgres
    POSTGRES_DB=EECE503N-planner
    DB_HOST=db
    DB_PORT=5432
    INIT_API_KEY=jasldfhasdkjfhs
    BACKEND_URL=http://backend:8000
        ```

    **Example `backend/.env`:**
    ```
    # Database Connection
    DATABASE_URL=postgresql://postgres:1234@db:5432/EECE503N-planner
    SECRET_KEY=your-secret-key-should-be-very-long-and-secure
    ALGORITHM=HS256
    ACCESS_TOKEN_EXPIRE_MINUTES=30

    INIT_API_KEY=jasldfhasdkjfhs

    # URL for the MCP Client service (used by the /chat endpoint)
    MCP_CLIENT_URL=http://mcp-client:3002
    MCP_SERVER_URL=http://mcp-server:9002
    ```

    **Example `mcp_client/.env`:**
    ```properties
    # filepath: /Users/ralphjabbour/Desktop/AUB/EECE503N/planner-ai/mcp_client/.env
    AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
    AZURE_OPENAI_KEY=<Your Azure OpenAI Key>
    AZURE_OPENAI_ENDPOINT=<Your Azure OpenAI Endpoint>
    AZURE_OPENAI_API_VERSION=2024-12-01-preview
    # URL for the MCP Server service
    MCP_SERVER_URL=http://mcp-server:3001
    ```

    **Example `iep-quiz/.env`:**
    ```
    AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
    AZURE_OPENAI_KEY=your-openai-api-key # Has to be from Azure
    AZURE_OPENAI_ENDPOINT=https://ryj01-m9bcjuyj-eastus2.cognitiveservices.azure.com/
    AZURE_OPENAI_API_VERSION=2024-12-01-preview
    ```

    **Example `behavior_analyzer/.env`:**
    ```properties
    DATABASE_URL=postgresql://postgres:1234@db:5432/EECE503N-planner
    SECRET_KEY=your-secret-key-should-be-very-long-and-secure
    ALGORITHM=HS256
    ACCESS_TOKEN_EXPIRE_MINUTES=30

    AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
    AZURE_OPENAI_KEY=
    AZURE_OPENAI_ENDPOINT=https://ryj01-m9bcjuyj-eastus2.cognitiveservices.azure.com/
    AZURE_OPENAI_API_VERSION=2024-12-01-preview
    ```

3.  Start the application:
    ```bash
    docker-compose up -d --build # Use --build initially or after changes
    ```

4.  Access the application:
    - Frontend: http://localhost:3000
    - Backend API Docs: http://localhost:8000/docs
    - Behavior Analyzer API: http://localhost:8001
    - IEP Quiz: http://localhost:9001 
    - MCP Client/Server typically don't have user-facing UIs but are accessed internally by other services.

## Components In-Depth

### Backend (`/backend`)
*   **Description:** A FastAPI application responsible for core business logic, user authentication, database interactions (managing students, courses, tasks, etc.), and serving the primary API consumed by the frontend. It includes the OR-Tools optimization logic and routes chat requests to the MCP Client.

### Frontend (`/frontend`)
*   **Description:** A React application providing the user interface. It interacts with the Backend API to display information and trigger actions, including the chat interface.

### MCP Server (`/mcp_server`)
*   **Description:** Implements the "Managed Component Protocol" (MCP) Server. It exposes database operations (like adding courses, registering students, managing tasks) as "tools" that can be called remotely by the MCP Client. It connects directly to the database using reflected models.

### MCP Client (`/mcp_client`)
*   **Description:** Acts as an intermediary between the Backend's chat endpoint and the AI model (Azure OpenAI). It receives a user query, connects to the MCP Server to discover available tools, interacts with the OpenAI API (sending the query and available tools), handles tool execution requests from OpenAI by calling the appropriate tool on the MCP Server, manages the conversation flow including multiple tool calls, and returns the final AI response to the Backend.

<!-- ... other sections like Running the App, Contributing, etc. ... -->

