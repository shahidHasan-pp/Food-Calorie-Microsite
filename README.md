# Food Calorie Microsite

An AI-powered microsite where users upload a food photo and instantly receive calorie and macronutrient estimates.

## Tech Stack

| Layer      | Technology                        |
|------------|-----------------------------------|
| Frontend   | Plain HTML + CSS + Vanilla JS     |
| Backend    | FastAPI (Python)                  |
| Database   | PostgreSQL (async via asyncpg)    |
| Storage    | Local filesystem (`uploads/`)     |
| AI         | Google Gemini 1.5 Flash (Vision)  |

## Project Structure

```
Food-Calorie-Microsite/
├── backend/
│   ├── .env                        # Environment variables
│   ├── requirements.txt
│   ├── pytest.ini
│   ├── app/
│   │   ├── main.py                 # FastAPI app entry point
│   │   ├── core/
│   │   │   ├── config.py           # Settings (pydantic-settings)
│   │   │   └── logging_config.py   # Structured logging setup
│   │   ├── database/
│   │   │   ├── session.py          # Async SQLAlchemy engine + session
│   │   │   └── crud.py             # Device / Asset / Task CRUD
│   │   ├── models/
│   │   │   ├── models.py           # ORM models
│   │   │   └── schemas.py          # Pydantic response schemas
│   │   ├── routers/
│   │   │   └── food.py             # POST /api/analyze-food
│   │   └── services/
│   │       ├── gemini_service.py   # Gemini Vision API integration
│   │       └── image_service.py    # File validation + save
│   └── tests/
│       ├── test_food_api.py
│       └── test_gemini_service.py
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── app.js
└── uploads/                        # Created automatically at runtime
```

## Setup & Run Guide

Follow these steps to set up the project locally from scratch.

### 1. Clone the Repository

```bash
git clone https://github.com/shahidHasan-pp/Food-Calorie-Microsite/
cd Food-Calorie-Microsite
```

### 2. Database Setup (PostgreSQL)

Ensure you have PostgreSQL installed and running. Create a new database for the application:

```sql
-- Open psql or pgAdmin and run:
CREATE DATABASE food_calorie_db;
```

### 3. Backend Environment Setup

Create a Python virtual environment and install dependencies:

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Configure Environment Variables

1. Inside the `backend/` directory, create a file named `.env`.
2. Add the following configurations (update the `GEMINI_API_KEY` and DB credentials if necessary):

```ini
# App
APP_NAME="Food Calorie Microsite"
APP_VERSION="1.0.0"
DEBUG=true

# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=food_calorie_db
DB_USER=postgres
DB_PASSWORD=postgres

# Gemini Vision API
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3-flash-preview

# File Upload
UPLOAD_DIR=uploads
MAX_FILE_SIZE_MB=10
```

### 5. Run Database Migrations

We use Alembic to manage database schema changes. To build the required database tables, run:

```bash
# Ensure your virtual environment is activated
alembic upgrade head
```

### 6. Run the Application

Start the FastAPI server using Uvicorn:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- **Frontend Application**: The site is served directly via the backend. Open your browser and go to **[http://localhost:8000](http://localhost:8000)**.
- **Interactive API Docs**: Swagger UI is available at **[http://localhost:8000/docs](http://localhost:8000/docs)**.

### 7. Run Tests

To execute the unit tests for the endpoints and AI services:

```bash
# Ensure your virtual environment is still active
pytest -v
```

## API Endpoints

| Method | Path                | Description                     |
|--------|---------------------|---------------------------------|
| GET    | `/api/health`       | Health check                    |
| POST   | `/api/analyze-food` | Analyze food image with Gemini  |
| GET    | `/api/docs`         | Swagger UI                      |

### POST `/api/analyze-food`

**Request** (`multipart/form-data`):
- `image` — JPEG / PNG / WEBP, max 10MB
- `device_id` — UUID string from browser localStorage

**Response**:
```json
{
  "success": true,
  "food_name": "Chicken Biryani",
  "calories": 420,
  "protein": 18,
  "carbs": 55,
  "fat": 15,
  "sugar": 4,
  "confidence_score": 88
}
```

## Database Schema

| Table     | Purpose                              |
|-----------|--------------------------------------|
| `devices` | Track devices by `device_id` (UUID)  |
| `assets`  | Store image metadata + file path     |
| `tasks`   | Store AI task status + JSON response |

## Design Patterns Used

| Pattern   | Where                          | Why                                         |
|-----------|--------------------------------|---------------------------------------------|
| Facade    | `routers/food.py`              | Single endpoint orchestrates all sub-systems |
| Strategy  | `services/gemini_service.py`   | Prompt composition isolated from HTTP call   |
| Repository| `database/crud.py`             | Database access abstracted from business logic|
| Singleton | `core/config.py` (`lru_cache`) | Settings loaded once, reused everywhere      |

## Security Notes

- Gemini API key stored in `.env`, never exposed to frontend
- File type validated by MIME type string AND extension
- File size validated server-side (not only headers)
- Device identified by client-generated UUID — no login required
- CORS configured (open by default for local dev — restrict in production)

