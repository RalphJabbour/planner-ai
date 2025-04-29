# Planner AI

https://github.com/user-attachments/assets/7227e21d-2dd8-472d-b9cd-cca6fa904f15



Planner AI is a comprehensive academic planning and course management system designed to help students organize their educational journey. The application features course synchronization, behavior analysis, interactive quizzes, and personalized planning tools.

## 🚀 Features

- **Course Management**: Track and manage academic courses
- **Intelligent Planning**: AI-powered planning suggestions
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
- **Backend**: Core FastAPI application
- **Behavior Analyzer**: ML-powered analysis of student behavior
- **Course Sync**: Automated course data synchronization
- **IEP Quiz**: Interactive quiz system
- **Database**: PostgreSQL data storage

## 🏗️ Architecture

The application is built using a microservices architecture with Docker, allowing each component to scale independently.

## 🚀 Getting Started

### Prerequisites

- Docker and Docker Compose
- Git

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/planner-ai.git
   cd planner-ai
   ```

2. Create environment files:
   - Create `.env` in the root directory
   - Create `backend/.env` 
   - Create `iep-quiz/.env`
   - Create `behavior_analyzer/.env`

   **Example `.env` (root directory):**
   ```
    POSTGRES_PASSWORD=1234
    POSTGRES_USER=postgres
    POSTGRES_DB=EECE503N-planner
   ```

   **Example `backend/.env`:**
   ```
   # Database Connection
    DATABASE_URL=postgresql://postgres:1234@db:5432/EECE503N-planner
    SECRET_KEY=your-secret-key-should-be-very-long-and-secure
    ALGORITHM=HS256
    ACCESS_TOKEN_EXPIRE_MINUTES=30
   ```

   **Example `iep-quiz/.env`:**
   ```
    AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
    AZURE_OPENAI_KEY=your-openai-api-key # Has to be from Azure
    AZURE_OPENAI_ENDPOINT=https://ryj01-m9bcjuyj-eastus2.cognitiveservices.azure.com/
    AZURE_OPENAI_API_VERSION=2024-12-01-preview
   ```

   **Example `behavior_analyzer/.env`:**
   ```
    DATABASE_URL=postgresql://postgres:1234@db:5432/EECE503N-planner
   ```

3. Start the application:
   ```bash
   docker-compose up -d
   ```

4. Access the application:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - Behavior Analyzer API: http://localhost:8001
   - IEP Quiz: http://localhost:9001

