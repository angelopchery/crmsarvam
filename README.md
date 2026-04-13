# CRMSarvam

A production-grade **CRM + ERP hybrid system** with AI-powered transcription and task intelligence.

## Features

- **User Management**: Admin and user roles with JWT authentication
- **Client & POC Management**: Track clients and points of contact
- **Event Tracking**: Log meetings, calls, and other interactions
- **Media Uploads**: Support for audio, video, and documents
- **AI Transcription**: Automatic speech-to-text using Sarvam AI Saaras v3
- **Intelligence Extraction**: Extract follow-ups and deadlines from transcripts
- **Calendar / To-Do System**: Tasks derived from deadlines with calendar view

## Tech Stack

### Backend
- **Python 3.11+**
- **FastAPI** - Modern, fast web framework
- **PostgreSQL** - Relational database
- **SQLAlchemy 2.0** - Async ORM
- **Alembic** - Database migrations
- **Celery + Redis** - Background task processing
- **FFmpeg** - Media processing (video to audio extraction)

### Frontend
- **React** with Vite
- **TailwindCSS** - Utility-first CSS framework
- **Calendar UI** - Microsoft Teams-like day/week view

### External Services
- **Sarvam AI** - Saaras v3 transcription API

## Architecture

```
app/
├── core/           # Configuration, security, database
├── models/         # SQLAlchemy ORM models
├── schemas/        # Pydantic validation schemas
├── services/       # Business logic layer
├── providers/      # External API integrations
├── workers/        # Celery background workers
└── routers/        # FastAPI API endpoints
```

## Installation

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Redis 7+
- FFmpeg (for media processing)

### 1. Clone the repository

```bash
git clone <repository-url>
cd CRMSarvam
```

### 2. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables

```bash
cp .env.example .env
# Edit .env with your configuration
```

Required variables:
- `DATABASE_URL` - PostgreSQL connection string
- `SECRET_KEY` - JWT secret key
- `SARVAMAI_API_KEY` - Sarvam AI API key
- `REDIS_URL` - Redis connection string

### 5. Initialize database

```bash
# Run Alembic migrations
alembic upgrade head
```

### 6. Create admin user

Use the API to create the first admin user:

```bash
curl -X POST http://localhost:8000/api/users \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "secure_password",
    "role": "admin"
  }'
```

Or use the provided script (after creating a temporary admin):

```python
from app.core.database import async_session_maker
from app.core.security import get_password_hash
from app.models.user import User

async def create_admin():
    async with async_session_maker() as db:
        admin = User(
            username="admin",
            hashed_password=get_password_hash("admin123"),
            role="admin",
            is_active=True,
        )
        db.add(admin)
        await db.commit()

import asyncio
asyncio.run(create_admin())
```

## Running the Application

### Start the API server

```bash
uvicorn app.main:app --reload
```

API will be available at: http://localhost:8000

### Start Celery worker

```bash
celery -A app.workers.celery_app worker --loglevel=info --concurrency=2
```

### Start Celery beat (optional, for scheduled tasks)

```bash
celery -A app.workers.celery_app beat --loglevel=info
```

## API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### Authentication
- `POST /api/auth/login` - User login
- `GET /api/auth/me` - Get current user
- `POST /api/auth/logout` - Logout

### Users
- `GET /api/users` - List users (admin only)
- `GET /api/users/{id}` - Get user details
- `POST /api/users` - Create user (admin only)
- `PUT /api/users/{id}` - Update user
- `DELETE /api/users/{id}` - Delete user (admin only)

### Clients
- `GET /api/clients` - List clients
- `GET /api/clients/{id}` - Get client with details
- `POST /api/clients` - Create client
- `PUT /api/clients/{id}` - Update client
- `DELETE /api/clients/{id}` - Delete client

### POCs (Points of Contact)
- `GET /api/pocs` - List POCs
- `GET /api/pocs/{id}` - Get POC details
- `POST /api/pocs` - Create POC
- `PUT /api/pocs/{id}` - Update POC
- `DELETE /api/pocs/{id}` - Delete POC

### Events
- `GET /api/events` - List events
- `GET /api/events/{id}` - Get event with all details
- `POST /api/events` - Create event
- `PUT /api/events/{id}` - Update event
- `DELETE /api/events/{id}` - Delete event
- `GET /api/events/{id}/media` - List event media
- `POST /api/events/{id}/media` - Upload media file
- `DELETE /api/events/media/{id}` - Delete media
- `GET /api/events/media/{id}/download` - Download media file

### Intelligence
- `GET /api/intelligence/follow-ups` - List follow-ups
- `POST /api/intelligence/follow-ups` - Create follow-up
- `PUT /api/intelligence/follow-ups/{id}` - Update follow-up
- `DELETE /api/intelligence/follow-ups/{id}` - Delete follow-up

- `GET /api/intelligence/deadlines` - List deadlines (or upcoming)
- `POST /api/intelligence/deadlines` - Create deadline
- `PUT /api/intelligence/deadlines/{id}` - Update deadline
- `DELETE /api/intelligence/deadlines/{id}` - Delete deadline

- `GET /api/intelligence/tasks` - List tasks (for calendar)
- `PUT /api/intelligence/tasks/{id}` - Update task status

## Transcription Flow

1. User uploads audio/video file to an event
2. System stores the file and creates `EventMedia` record
3. Celery task `process_transcription` is triggered
4. For videos: FFmpeg extracts audio
5. Audio is sent to Sarvam AI for transcription
6. Transcription is stored
7. Intelligence extraction runs:
   - Follow-ups are identified and stored
   - Deadlines are identified and stored
   - Tasks are created for each deadline

## Database Schema

```
users              - User accounts and roles
clients            - Client/organization information
pocs               - Points of contact for clients
events             - Meetings, calls, interactions
event_media        - Uploaded files for events
transcriptions     - AI-generated transcripts
follow_ups         - Action items from events
deadlines          - Due dates from events
tasks              - Task completion tracking
```

## Development

### Run tests

```bash
pytest
```

### Code formatting

```bash
black app/
isort app/
```

### Type checking

```bash
mypy app/
```

### Create a migration

```bash
alembic revision --autogenerate -m "description"
```

### Apply migrations

```bash
alembic upgrade head
```

## Production Deployment

### Docker

A `Dockerfile` and `docker-compose.yml` are recommended for production deployment.

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create uploads directory
RUN mkdir -p uploads

# Run with gunicorn
CMD ["gunicorn", "app.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
```

### Environment

- Set `DEBUG=False`
- Use strong `SECRET_KEY`
- Configure proper `CORS_ORIGINS`
- Set up proper file storage (S3 recommended)
- Configure Redis with persistence
- Set up PostgreSQL backups

### Monitoring

- Use application monitoring (Sentry, DataDog, etc.)
- Monitor Celery task queue
- Track transcription API usage
- Monitor disk usage for uploads

## Security Considerations

1. **Authentication**: JWT tokens with expiration
2. **Authorization**: Role-based access control (admin/user)
3. **Password Security**: bcrypt hashing
4. **File Uploads**: Size limits, type validation
5. **CORS**: Configurable origins
6. **SQL Injection**: Prevented by SQLAlchemy ORM
7. **Rate Limiting**: Consider adding for production

## License

MIT License - See LICENSE file for details

## Support

For issues and questions, please open an issue on the repository.
