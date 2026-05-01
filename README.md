# Book Recommender System

An AI-powered book recommendation system that combines **Large Language Models (LLMs)** with **embedding-based similarity search** to help users discover books through semantic understanding, mood-based queries, and thematic exploration.

**[Video Demo](https://drive.google.com/file/d/1iMLYHvfMU0ECTITtlwgHNjXtJGePy7fE/view?usp=sharing)**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---
## Quick Start

### Prerequisites

- **Backend**: Python 3.11+, Poetry, PostgreSQL, Redis
- **Frontend**: Node.js 18+, npm/yarn
- **Services**: OpenAI API key

### Backend Setup

```bash
cd backend

# Install dependencies
poetry install

# Set up environment variables
cp config/.env.example config/.env # Create this file with required variables

# Required environment variables:
# OPENAI_API_KEY=your_openai_api_key
# POSTGRES_HOST=localhost
# POSTGRES_PORT=5432
# POSTGRES_DB=book_recommender
# POSTGRES_USER=your_user
# POSTGRES_PASSWORD=your_password
# REDIS_HOST=localhost
# REDIS_PORT=6379

# Run the backend
poetry run uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Set up environment variables
# Create .env.local with:
# VITE_API_URL=http://localhost:8000

# Run the frontend
npm run dev
```

## Docker Deployment

### Local Development

```bash
# Backend
cd backend
docker build -t book-recommender-api .
docker run -p 8000:8000 --env-file .env book-recommender-api
```

### Cloud Run Deployment

```bash
cd backend
gcloud builds submit --config cloudbuild.yaml
```

The Cloud Run configuration is optimized for:
- Automatic scaling to zero
- Health checks and readiness probes
- Graceful shutdown handling

---

## Technology Stack

### Backend
- **Framework**: FastAPI 0.115+
- **LLM Integration**: OpenAI GPT-4
- **Database**: PostgreSQL with pgvector
- **Caching**: Redis
- **ORM**: SQLAlchemy (async)
- **Dependencies**: Poetry

### Frontend
- **Framework**: React 19
- **Build Tool**: Vite 7
- **Styling**: TailwindCSS 4
- **Routing**: React Router 7
- **Visualization**: Mermaid diagrams

### Infrastructure
- **Backend Hosting**: Google Cloud Run
- **Frontend Hosting**: Firebase Hosting
- **Database**: Cloud SQL (PostgreSQL)
- **Container Registry**: Google Container Registry

---

## Project Structure

```
Book-Recommender/
├── backend/
│   ├── app/                   # Application code
│   │   ├── api/               # API routes and schemas
│   │   ├── clients/           # OpenAI and external clients
│   │   ├── config/            # Settings and logging
│   │   ├── db/                # Database connections
│   │   ├── domains/           # Domain models (books, etc.)
│   │   ├── orchestration/     # Task orchestration engine
│   │   ├── pipeline/          # Processing pipeline nodes
│   │   ├── state/             # State management
│   │   └── stores/            # Data stores and repositories
│   ├── config/                # Environment files (git-ignored locally)
│   ├── infra/                 # Infrastructure & deployment
│   ├── data/                  # Data files and examples
│   ├── Makefile
│   └── pyproject.toml
│
├── frontend/
│   ├── src/
│   │   ├── components/        # React components
│   │   ├── pages/             # Page components
│   │   ├── utils/             # Utilities
│   │   ├── api.js             # API client (uses VITE_BACKEND_URL)
│   ├── public/
│   │   └── blog-posts/        # Documentation & diagrams
│   ├── package.json
│   ├── vite.config.js
│   └── Dockerfile
│
└── README.md
```

---

## Features

### Current Features
- Natural language book search
- Semantic similarity recommendations
- Mood and theme-based queries
- Book comparison and analysis
- Real-time streaming responses
- Interactive chat interface
- Task visualization with Mermaid diagrams

### Planned Features
- User reading history tracking
- Personalized recommendation tuning
- Community ratings integration
- Advanced filtering options
- Reading list management

---

## Example Queries

```
"Find horror novels similar to It by Stephen King"

"Recommend books with the same vibes as The Great Gatsby"

"Compare Dune and The Iliad based on themes and complexity"

"I want something philosophical but easy to read"
```

---

## Contributing

This is a public release of a personal project. Feedback and suggestions are welcome!

**Contact**: tuanqpham0921@gmail.com

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---
