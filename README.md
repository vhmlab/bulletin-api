# Boletin Service API

A FastAPI service for managing church service bulletins with Google OAuth authentication and SQLite database.

## Features

- 🔐 Google OAuth 2.0 authentication
- 📊 Four service types: Sabbath School, Worship Service, Youth Service, Wednesday Service
- 💾 SQLite database for data persistence
- 📝 JSON data storage in text fields
- 🚀 RESTful API with full CRUD operations
- 📚 Auto-generated API documentation (Swagger UI)

## Prerequisites

- Python 3.8 or higher
- Google Cloud Platform account (for OAuth credentials)

## Setup Instructions

### 1. Install Dependencies

```bash
# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### 2. Configure Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google+ API
4. Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client ID"
5. Configure OAuth consent screen if not already done
6. Select "Web application" as application type
7. Add authorized redirect URI: `http://localhost:8000/auth/callback`
8. Copy the Client ID and Client Secret

### 3. Environment Configuration

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
GOOGLE_CLIENT_ID=your-actual-client-id
GOOGLE_CLIENT_SECRET=your-actual-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback
SECRET_KEY=your-secret-key-change-this-to-a-random-string
DATABASE_URL=sqlite:///./boletin.db
```

**Important:** Generate a secure SECRET_KEY:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 4. Run the Application

```bash
python main.py
```

Or using uvicorn directly:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at: `http://localhost:8000`

## Authentication Flow

### 1. Login with Google

Navigate to: `http://localhost:8000/auth/login`

This will redirect you to Google's login page. After successful authentication, you'll receive a JSON response with an access token:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "email": "user@example.com",
    "name": "John Doe"
  }
}
```

### 2. Use the Access Token

Include the token in the Authorization header for all API requests:

```
Authorization: Bearer YOUR_ACCESS_TOKEN
```

## API Endpoints

### Documentation

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Authentication Endpoints

- `GET /auth/login` - Initiate Google OAuth login
- `GET /auth/callback` - OAuth callback (handled automatically)
- `GET /auth/logout` - Logout information

### Service Endpoints

All service endpoints require authentication. Each service type has the same endpoint structure:

#### Sabbath School (`/sabbath_school`)
#### Worship Service (`/worship_service`)
#### Youth Service (`/youth_service`)
#### Wednesday Service (`/wednesday_service`)

**Available operations:**

- `POST /` - Create new entry
- `GET /` - Get all entries (with pagination)
- `GET /{entry_id}` - Get specific entry
- `GET /by-date/{date}` - Get entries by date
- `PUT /{entry_id}` - Update entry
- `DELETE /{entry_id}` - Delete entry

#### Patch JSON fields by date

Update one or more nested `value` objects inside the stored `data` list for all entries matching a given `date` (format: `yyyy-ww`).

- `PATCH /{service_type}/by-date/{date}/values` - Accepts a JSON array in the request body. Each element of the array should be a `value`-dictionary whose keys match the keys of an existing item's nested `value` object in the stored `data` list. If any incoming dict does not match for any entry, the request will fail.

Example: stored data (before):

```json
[{
  "name": {
    "Hymn": {"en": "Opening Hymn", "es": "Himno de Apertura"},
    "Song": {"en": "Opening Song", "es": "Canto de Apertura"}
  },
  "type": "hymn",
  "value": {"topic": 0, "sub": 0, "number": 2, "url": ""}
}, {
  "name": {"en": "Scripture Reading", "es": "Lectura Biblica"},
  "type": "scripture",
  "value": {"translation": 16, "book": "Genesis", "chapter": 1, "verse_start": 1, "verse_end": 1}
}]
```

Valid PATCH request body (only the nested `value` objects are sent):

```json
{
  "values": [
    {"topic": 0, "sub": 0, "number": 35, "url": ""},
    {"translation": 16, "book": "Genesis", "chapter": 2, "verse_start": 5, "verse_end": 5}
  ]
}
```

Stored data (after):

```json
[{
  "name": {"Hymn": {"en": "Opening Hymn", "es": "Himno de Apertura"}, "Song": {"en": "Opening Song", "es": "Canto de Apertura"}},
  "type": "hymn",
  "value": {"topic": 0, "sub": 0, "number": 35, "url": ""}
}, {
  "name": {"en": "Scripture Reading", "es": "Lectura Biblica"},
  "type": "scripture",
  "value": {"translation": 16, "book": "Genesis", "chapter": 2, "verse_start": 5, "verse_end": 5}
}]
```

cURL example:

```bash
curl -X PATCH "http://localhost:8000/worship_service/by-date/2026-04/values" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '[{"topic":0,"sub":0,"number":35,"url":""},{"translation":16,"book":"Genesis","chapter":2,"verse_start":5,"verse_end":5}]'
```

## API Usage Examples

### Create Entry

```bash
curl -X POST "http://localhost:8000/sabbath_school/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2026-04",
    "data": [
      {"name": "Opening Hymn", "type": "hymn", "value": {"topic": 0, "sub": 0, "number": 2, "url": ""}},
      {"name": "Scripture Reading", "type": "scripture", "value": {"translation": 16, "book": "Genesis", "chapter": 1, "verse_start": 1, "verse_end": 1}}
    ]
  }'
```

### Get All Entries

```bash
curl -X GET "http://localhost:8000/sabbath_school/?skip=0&limit=10" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Get Entry by ID

```bash
curl -X GET "http://localhost:8000/sabbath_school/1" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Get Entries by Date

```bash
curl -X GET "http://localhost:8000/sabbath_school/by-date/2026-04" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Update Entry

```bash
curl -X PUT "http://localhost:8000/sabbath_school/1" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "data": [
      {"name": "Updated Hymn", "type": "hymn", "value": {"topic": 1, "sub": 0, "number": 10, "url": ""}}
    ]
  }'
```

### Delete Entry

```bash
curl -X DELETE "http://localhost:8000/sabbath_school/1" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Data Format

Each service entry has two fields:

- **date**: Year-week string in `yyyy-ww` format (e.g., `2026-04`)
- **data**: JSON array stored as text string. Each element is typically an object describing a part of the bulletin (hymn, scripture, speaker, etc.).

Example `data` value:
```json
[
  {"name": "Opening Hymn", "type": "hymn", "value": {"topic": 0, "sub": 0, "number": 2, "url": ""}},
  {"name": "Scripture Reading", "type": "scripture", "value": {"translation": 16, "book": "Genesis", "chapter": 1, "verse_start": 1, "verse_end": 1}}
]
```

## Database

The application uses SQLite database (`boletin.db`) with four tables:
- `sabbath_school`
- `worship_service`
- `youth_service`
- `wednesday_service`

Each table has:
- `id` (Primary Key)
- `date` (DateTime, indexed)
- `data` (Text - stores JSON)

## Project Structure

```
boletin/
├── main.py              # FastAPI application entry point
├── config.py            # Configuration settings
├── database.py          # Database models and connection
├── schemas.py           # Pydantic schemas for validation
├── crud.py              # CRUD operations
├── routers.py           # API route handlers
├── auth.py              # Authentication logic
├── requirements.txt     # Python dependencies
├── .env.example         # Example environment variables
├── .gitignore          # Git ignore file
└── README.md           # This file
```

## Security Notes

- Never commit `.env` file to version control
- Change the `SECRET_KEY` in production
- Use HTTPS in production
- The access token expires after 30 minutes (configurable)
- Keep your Google OAuth credentials secure

## Development

### Testing with Swagger UI

1. Start the server
2. Go to `http://localhost:8000/docs`
3. Click "Authorize" button
4. Get your access token from `/auth/login`
5. Enter: `Bearer YOUR_ACCESS_TOKEN`
6. Test all endpoints interactively

## Troubleshooting

### "Could not validate credentials" error
- Check if your token has expired (30 minutes default)
- Login again to get a new token

### OAuth redirect issues
- Verify `GOOGLE_REDIRECT_URI` matches exactly with Google Console
- Check that the redirect URI is added to authorized URIs in Google Console

### Database errors
- Delete `boletin.db` and restart the application to recreate tables
- Check file permissions in the project directory

## License

MIT License - Feel free to use this project for your needs.
