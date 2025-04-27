# Planner AI - Intelligent Educational Scheduling System

Planner AI is an advanced scheduling and learning management system designed specifically for students. It integrates multiple intelligent components to optimize study time, provide personalized learning experiences, and help students manage their academic obligations effectively.

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Project Structure](#project-structure)
- [Intelligent Educational Plugins (IEPs)](#intelligent-educational-plugins-ieps)
  - [OR-Tools Scheduler](#or-tools-scheduler)
  - [Study Time Estimator](#study-time-estimator)
  - [Quiz Generator](#quiz-generator)
  - [AI Chatbot & MCP](#ai-chatbot--mcp)
  - [Behavioral IEP](#behavioral-iep)
- [Setup Instructions](#setup-instructions)
- [Environment Variables](#environment-variables)
- [API Documentation](#api-documentation)
- [Contributing](#contributing)

## Overview

Planner AI is a comprehensive student planning system that uses artificial intelligence to optimize study schedules, estimate workloads, and provide personalized learning experiences. The system integrates course management, flexible and fixed obligation tracking, and intelligent task scheduling to create an optimal study plan for students.

## Key Features

- **Intelligent Scheduling**: Automatically allocates study time based on course workload and student preferences
- **Content Analysis**: Analyzes PDF documents to extract key concepts and estimate study time
- **Personalized Quizzes**: Generates knowledge assessments based on learning materials
- **AI Chatbot**: Provides intelligent assistance for student questions
- **Academic Planning**: Manages fixed and flexible obligations in an optimized calendar

## Project Structure

The project follows a microservices architecture with the following main components:

- **Frontend**: React-based web interface (`/frontend`)
- **Backend**: FastAPI Python service managing core logic (`/backend`)
- **IEP Services**: Specialized AI services for specific educational functions
  - OR-Tools Scheduler
  - PDF Analysis & Study Time Estimation
  - Quiz Generation
  - Conversational AI (MCP)
  - Behavioral Analysis

## Intelligent Educational Plugins (IEPs)

### OR-Tools Scheduler

The OR-Tools Scheduler is the core optimization engine that intelligently allocates study time in the student's calendar.

**Key Features:**

- Constraint-based scheduling using Google OR-Tools
- Handles both fixed obligations (classes, work) and flexible obligations (study time)
- Prioritizes tasks based on deadlines and importance
- Respects student preferences for study times and breaks
- Re-optimizes when new obligations are added

**Implementation:**

- Location: `/backend/app/or_tools/`
- Key files: `scheduler.py`, `constraints.py`
- Integration point: `/backend/app/routers/tasks.py` for schedule updates

### Study Time Estimator

This IEP analyzes PDF documents to estimate the amount of study time required for mastery.

**Key Features:**

- Converts PDF documents to images for AI processing
- Uses Azure OpenAI's vision capabilities to analyze document complexity
- Estimates required study hours based on content, length, and complexity
- Creates flexible obligations with appropriate time allocations
- Graceful fallbacks when AI service is unavailable

**Implementation:**

- Location: `/iep-quiz/`
- Frontend component: `/frontend/src/components/MaterialsQuiz/StudyTimeEstimator.jsx`
- API endpoints:
  - `/estimate-study-time`

**Environment Setup:**
When first setting up, create `iep-quiz/.env` file with:

```bash
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
AZURE_OPENAI_KEY=your-openai-api-key
AZURE_OPENAI_ENDPOINT=https://ryj01-m9bcjuyj-eastus2.cognitiveservices.azure.com/
AZURE_OPENAI_API_VERSION=2024-12-01-preview
```

### Quiz Generator

The Quiz Generator creates personalized assessment materials based on course content and student knowledge gaps.

**Key Features:**

- Extracts key concepts from PDF learning materials
- Allows students to rate their knowledge on extracted concepts
- Generates tailored quiz questions focusing on knowledge gaps
- Provides immediate feedback and learning recommendations
- Tracks concept mastery over time

**Implementation:**

- Location: `/iep-quiz/`
- Frontend component: `/frontend/src/components/MaterialsQuiz/MaterialsQuizPage.jsx`
- API endpoints:
  - `/extract-ideas`

### AI Chatbot & MCP

The AI Chatbot and Model Control Protocol (MCP) provide conversational assistance to students.

**Key Features:**

- Natural language interface for student questions
- Context-aware responses using course materials and calendar information
- Answers academic questions and provides scheduling assistance
- MCP implementation ensures consistent and reliable AI responses
- Maintains conversation history for continuity

**Implementation:**

- Location: `/backend/app/routers/chat.py` and `/backend/mcp_server.py`
- Frontend integration: Chatbot interface in dashboard
- Uses stateful conversation tracking

### Behavioral IEP

The Behavioral IEP analyzes student study patterns and provides optimization recommendations.

**Key Features:**

- Tracks actual vs. planned study time
- Identifies productivity patterns and optimal study times
- Recommends schedule adjustments based on performance data
- Integrates with the OR-Tools scheduler for adaptive scheduling
- Currently implemented but requires integration fixes

**Implementation:**

- Status: Implementation complete but showing integration errors
- Planned integration points: Schedule optimization and recommendation system

## Setup Instructions

1. **Clone the repository**

   ```bash
   git clone https://github.com/RalphJabbour/planner-ai
   cd planner-ai
   ```

2. **Set up environment variables**
   Create necessary environment files as described in the Environment Variables section.

3. **Run with Docker Compose**

   ```bash
   docker-compose up --build
   ```

4. **Access the application**
   Open your browser and navigate to `http://localhost:3000`

## Environment Variables

Several services require environment variables to be set up:

1. **IEP-Quiz** (PDF analysis, study time estimation)
   Create `iep-quiz/.env` with:

   ```bash
   AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
   AZURE_OPENAI_KEY=your-openai-api-key
   AZURE_OPENAI_ENDPOINT=https://ryj01-m9bcjuyj-eastus2.cognitiveservices.azure.com/
   AZURE_OPENAI_API_VERSION=2024-12-01-preview
   ```

2. **Backend** settings can be configured in `backend/.env`
    ```bash
    DATABASE_URL=postgresql://postgres:1234@db:5432/EECE503N-planner
    SECRET_KEY=your-secret-key-should-be-very-long-and-secure
    ALGORITHM=HS256
    ACCESS_TOKEN_EXPIRE_MINUTES=30
    ```

3. **PLANNER_AI: main directory** 
    ```bash
    POSTGRES_PASSWORD=1234
    POSTGRES_USER=postgres
    POSTGRES_DB=EECE503N-planner   
    ``` 
    

## API Documentation

When the application is running, API documentation is available at:

- Backend API: `http://localhost:8000/docs`
- IEP Quiz API: `http://localhost:9001/docs`

## Contributing

1. Fork the project
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
