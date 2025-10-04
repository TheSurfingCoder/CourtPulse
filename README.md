# CourtPulse

A sports court discovery and management platform - similar to Surfline.com but for all sports.

## 🚀 Staging Environment
- **Backend**: https://courtpulse-staging-backend.onrender.com
- **Frontend**: https://courtpulse-staging.vercel.app

## 🏗️ Architecture

- **Frontend**: Next.js 14 with TypeScript
- **Backend**: Express.js with TypeScript
- **Database**: PostgreSQL with PostGIS for spatial data
- **Documentation**: Swagger/OpenAPI
- **Testing**: Jest with unit and integration tests

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ 
- PostgreSQL 12+ with PostGIS extension
- npm 9+

### 1. Clone and Install Dependencies

```bash
git clone <repository-url>
cd CourtPulse
npm install
```

### 2. Environment Setup

#### Backend
```bash
cd backend
cp .env.example .env
# Edit .env with your database credentials
```

#### Frontend
```bash
cd frontend
cp .env.example .env
# Edit .env with your API configuration
```

### 3. Database Setup

```bash
# Create database and enable PostGIS
createdb courtpulse
psql courtpulse -c "CREATE EXTENSION postgis;"

# Run migrations
cd backend
npm run migrate
```

### 4. Start Development Servers

```bash
# From root directory
npm run dev

# Or individually:
npm run dev:backend    # Backend on port 5000
npm run dev:frontend   # Frontend on port 3000
```

## 📚 API Documentation

Once the backend is running, visit:
- **Swagger UI**: http://localhost:5000/api-docs
- **Health Check**: http://localhost:5000/health

## 🧪 Testing

```bash
cd backend

# Run all tests
npm test

# Run tests in watch mode
npm run test:watch

# Generate coverage report
npm run test:coverage

# Run tests for CI
npm run test:ci
```

## 🐳 Docker

```bash
# Development
npm run docker:dev

# Staging
npm run docker:staging

# Production
npm run docker:prod
```

## 📁 Project Structure

```
├── backend/                 # Express.js API server
│   ├── src/
│   │   ├── controllers/    # Route controllers
│   │   ├── middleware/     # Custom middleware
│   │   ├── models/         # Database models
│   │   ├── routes/         # API routes
│   │   └── utils/          # Utility functions
│   ├── tests/              # Test files
│   └── config/             # Configuration files
├── frontend/               # Next.js application
│   ├── app/               # App router pages
│   ├── components/        # React components
│   └── types/            # TypeScript types
└── docker/                # Docker configurations
```

## 🔧 Available Scripts

### Root Level
- `npm run dev` - Start both frontend and backend in development
- `npm run build` - Build both frontend and backend
- `npm run start` - Start both frontend and backend in production

### Backend
- `npm run dev` - Start development server with hot reload
- `npm run test` - Run test suite
- `npm run migrate` - Run database migrations
- `npm run lint` - Run ESLint

### Frontend
- `npm run dev` - Start Next.js development server
- `npm run build` - Build for production
- `npm run start` - Start production server

## 🌍 Environment Variables

### Backend (.env)
```env
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=courtpulse
DB_USER=postgres
DB_PASSWORD=your_password

# Server
PORT=5000
NODE_ENV=development

# Security
JWT_SECRET=your_secret_key
CORS_ORIGIN=http://localhost:3000
```

### Frontend (.env)
```env
NEXT_PUBLIC_API_URL=http://localhost:5000
NEXT_PUBLIC_API_VERSION=v1
```

## 🚀 Deployment

### Backend
```bash
cd backend
npm run build
npm start
```

### Frontend
```bash
cd frontend
npm run build
npm start
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## 📝 License

This project is licensed under the MIT License.
# Test
# Test 2
# Test 3
# Test 4
# Test commit hooks
