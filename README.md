# Anti-Leak API

A secure FastAPI application for managing and distributing protected Lua scripts with features for authentication, telemetry, and script chunking.

## Features

- Secure script distribution with encryption and signing
- Authentication system with JWT tokens
- Rate limiting and request validation
- Telemetry tracking
- Health monitoring and metrics
- Key rotation management
- Secure secrets management with HashiCorp Vault
- Database migrations with Alembic
- Comprehensive logging with structlog

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL
- **Cache**: Redis
- **Secrets Management**: HashiCorp Vault
- **Container Runtime**: Docker & Docker Compose
- **Database Migrations**: Alembic
- **Testing**: pytest
- **Logging**: structlog

## Project Structure

```
.
├── alembic/                 # Database migration files
├── app/                     # Main application code
│   ├── api/                # API endpoints
│   ├── core/               # Core functionality (config, logging, etc.)
│   ├── middleware/         # Custom middleware
│   ├── models/             # SQLAlchemy models
│   ├── monitoring/         # Health checks and metrics
│   ├── schemas/            # Pydantic models
│   ├── services/           # Business logic
│   └── utils/              # Utility functions
└── tests/                  # Test suite
```

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.12+
- PostgreSQL 16.1+
- Redis 7.4+
- HashiCorp Vault 1.18+

### Environment Setup

1. Clone the repository:
```bash
git clone https://github.com/Stupidoodle/lua-anti-leak
cd anti-leak-api
```

2. Create environment files:
```bash
cp .env.example .env.dev
cp .env.example .env.prod
```

3. Update the environment variables in `.env.dev` and `.env.prod` with your configuration.

### Running with Docker Compose

1. Start the services:
```bash
docker-compose up -d
```

2. Run database migrations:
```bash
alembic upgrade head
```

### Development Setup

1. Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Start the development server:
```bash
uvicorn app.main:app --reload --port 8000
```

## API Documentation

Once the server is running, you can access:
- Swagger UI documentation: `http://localhost:8000/docs`
- ReDoc documentation: `http://localhost:8000/redoc`

## Key Features Explained

### Script Distribution

The API securely distributes Lua scripts by:
1. Chunking the script into smaller pieces
2. Encrypting each chunk with AES-GCM
3. Signing the encrypted data with RSA
4. Distributing chunks with authentication and rate limiting

### Authentication Flow

1. Client authenticates with user credentials
2. Server validates credentials and issues a JWT token
3. Client uses the token for subsequent requests
4. Each request is validated and rate-limited

### Key Management

- RSA key pairs are managed through HashiCorp Vault
- Automatic key rotation is implemented
- Ephemeral AES keys are generated for each session

### Security Features

- Request validation and sanitization
- Rate limiting with Redis
- Comprehensive logging and monitoring
- Secure headers middleware
- Database connection pooling
- Input validation with Pydantic

## Monitoring

### Health Checks

Access the health endpoint at `/monitoring/health` to check:
- Database connectivity
- Redis status
- Vault status
- Service health metrics

### Metrics

Prometheus metrics are available at `/metrics` when enabled, tracking:
- Request counts and latencies
- Failed authentication attempts
- Key rotation events
- Custom business metrics

## Testing

Run the test suite:
```bash
pytest
```

For integration tests:
```bash
pytest tests/integration
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request
