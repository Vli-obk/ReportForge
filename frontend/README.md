# PDF Analytics Platform

A complete AI-powered PDF Analytics Platform built with Next.js, FastAPI, and PostgreSQL. Upload PDFs, scrape from URLs, extract data with OCR, transform into datasets, and visualize analytics in a modern SaaS interface.

## 🚀 Features

### Frontend (Next.js 15)
- **Modern SaaS UI** - Premium design with glassmorphism and smooth animations
- **Authentication** - Login, Register, Forgot Password with JWT tokens
- **Dashboard** - Real-time KPIs and statistics
- **PDF Upload Center** - Drag & drop, URL scraping, OCR toggle
- **Dataset Explorer** - Searchable tables, pagination, filters, CSV/JSON export
- **Analytics Dashboard** - Interactive charts with Recharts (bar, line, pie)
- **Pipeline Monitoring** - Job status, processing logs, health checks
- **Settings** - API configuration, OCR settings, upload preferences

### Backend (FastAPI)
- **PDF Scraping** - Download PDFs from URLs with validation and retries
- **PDF Extraction** - Text and table extraction with pdfplumber
- **OCR Support** - Tesseract OCR for scanned PDFs
- **Data Transformation** - Pandas-based cleaning and normalization
- **PostgreSQL** - SQLAlchemy models with proper relationships
- **REST API** - Comprehensive endpoints for all operations
- **Authentication** - JWT-based auth with password hashing

### DevOps
- **Docker** - Complete containerization with docker-compose
- **PostgreSQL** - Persistent database storage
- **Production Ready** - Optimized builds and configurations

## 🛠️ Quick Start with Docker

The easiest way to run the entire application is with Docker:

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

This will start:
- **Frontend** on http://localhost:4028
- **Backend API** on http://localhost:8000
- **PostgreSQL** on port 5432
- **API Docs** at http://localhost:8000/api/v1/docs

## 🛠️ Manual Installation

### Prerequisites
- Node.js 20+
- Python 3.11+
- PostgreSQL 15+
- Tesseract OCR (for OCR functionality)

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run database migrations (if using Alembic)
alembic upgrade head

# Start backend server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

Open [http://localhost:4028](http://localhost:4028) in your browser.

## 📁 Project Structure

```
.
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── api/               # API endpoints
│   │   │   └── v1/           # API v1 routes
│   │   ├── core/             # Configuration and security
│   │   ├── database/         # Database session
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── scraper/          # PDF scraping logic
│   │   ├── services/         # Business logic
│   │   ├── transformers/     # Data transformation
│   │   └── main.py           # FastAPI app
│   ├── requirements.txt      # Python dependencies
│   ├── Dockerfile           # Backend Docker config
│   └── .env                 # Backend environment variables
├── src/                      # Next.js frontend
│   ├── app/
│   │   ├── home/            # Dashboard pages
│   │   │   ├── components/  # Page components
│   │   │   ├── dashboard/   # Dashboard route
│   │   │   ├── uploads/     # Uploads route
│   │   │   ├── datasets/    # Datasets route
│   │   │   ├── analytics/   # Analytics route
│   │   │   ├── pipeline/    # Pipeline route
│   │   │   └── settings/    # Settings route
│   │   ├── AuthProvider.tsx # Authentication context
│   │   └── layout.tsx       # Root layout
│   ├── components/          # Reusable components
│   │   ├── Header.tsx       # Landing page header
│   │   ├── Sidebar.tsx      # Dashboard sidebar
│   │   ├── TopNav.tsx       # Dashboard top nav
│   │   └── ui/              # UI components
│   ├── lib/                 # Utilities and API client
│   │   ├── api.ts           # Axios API client
│   │   └── utils.ts         # Helper functions
│   └── styles/              # Global styles
├── docker-compose.yml       # Docker orchestration
├── Dockerfile              # Frontend Docker config
├── package.json            # Frontend dependencies
└── next.config.mjs         # Next.js configuration
```

## 🎨 Tech Stack

### Frontend
- **Next.js 15** - React framework with App Router
- **React 19** - UI library
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling
- **Framer Motion** - Animations
- **Recharts** - Data visualization
- **Axios** - HTTP client
- **Lucide React** - Icons

### Backend
- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - ORM
- **PostgreSQL** - Database
- **Pydantic** - Data validation
- **pdfplumber** - PDF extraction
- **pandas** - Data manipulation
- **pytesseract** - OCR
- **python-jose** - JWT authentication
- **passlib** - Password hashing

### DevOps
- **Docker** - Containerization
- **docker-compose** - Multi-container orchestration

## 📦 Available Scripts

### Frontend
- `npm run dev` - Start development server on port 4028
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint
- `npm run lint:fix` - Fix ESLint issues
- `npm run format` - Format with Prettier

### Backend
- `uvicorn app.main:app --reload` - Start development server
- `uvicorn app.main:app --host 0.0.0.0 --port 8000` - Start production server

## 🔐 Environment Variables

### Frontend (.env)
```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

### Backend (backend/.env)
```env
POSTGRES_SERVER=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=pdf_analytics
SECRET_KEY=your-secret-key-change-in-production
BACKEND_CORS_ORIGINS=["http://localhost:4028"]
```

## 📊 API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login user
- `GET /api/v1/auth/me` - Get current user

### PDFs
- `POST /api/v1/pdfs/upload` - Upload PDF file
- `POST /api/v1/pdfs/scrape` - Scrape PDF from URL
- `GET /api/v1/pdfs` - Get all PDFs
- `GET /api/v1/pdfs/{id}` - Get specific PDF
- `DELETE /api/v1/pdfs/{id}` - Delete PDF
- `GET /api/v1/pdfs/statistics/overview` - Get statistics

### Datasets
- `GET /api/v1/datasets` - Get all datasets
- `GET /api/v1/datasets/{id}` - Get specific dataset
- `GET /api/v1/datasets/{id}/rows` - Get dataset rows
- `DELETE /api/v1/datasets/{id}` - Delete dataset

### Pipeline
- `GET /api/v1/pipeline/jobs` - Get processing jobs
- `GET /api/v1/pipeline/jobs/{id}` - Get specific job
- `GET /api/v1/pipeline/health` - Get pipeline health

## 🚢 Deployment

### Docker Deployment
```bash
docker-compose up -d
```

### Manual Deployment

1. **Backend**: Deploy to a server with Python 3.11+, PostgreSQL, and Tesseract
2. **Frontend**: Build with `npm run build` and deploy to Vercel, Netlify, or any Node.js host
3. **Database**: Use managed PostgreSQL (AWS RDS, Google Cloud SQL, etc.)
4. **Environment**: Set proper environment variables for production

## 📝 License

This project is proprietary software.

## 🙏 Acknowledgments

- Built with modern web technologies
- Inspired by enterprise SaaS platforms
- Designed for scalability and performance