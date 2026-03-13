# Documentation Platform - API Examples

## Authentication

### Login
```bash
curl -X POST http://localhost:8001/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### Using the Token
```bash
# Set token as environment variable
export TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# Use in requests
curl http://localhost:8001/api/v1/documents \
  -H "Authorization: Bearer $TOKEN"
```

### Refresh Token
```bash
curl -X POST http://localhost:8001/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}'
```

### Get Current User
```bash
curl http://localhost:8001/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

---

## Documents

### List Documents
```bash
# Basic list
curl http://localhost:8001/api/v1/documents \
  -H "Authorization: Bearer $TOKEN"

# With pagination
curl "http://localhost:8001/api/v1/documents?page=1&page_size=10" \
  -H "Authorization: Bearer $TOKEN"

# Filter by status
curl "http://localhost:8001/api/v1/documents?status=active" \
  -H "Authorization: Bearer $TOKEN"

# Search
curl "http://localhost:8001/api/v1/documents?search=policy" \
  -H "Authorization: Bearer $TOKEN"
```

### Create Document
```bash
curl -X POST http://localhost:8001/api/v1/documents \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Safety Guidelines",
    "document_number": "DOC-SAFETY-001",
    "description": "Company safety procedures",
    "category": "safety",
    "status": "draft"
  }'
```

### Get Single Document
```bash
curl http://localhost:8001/api/v1/documents/1 \
  -H "Authorization: Bearer $TOKEN"
```

### Update Document
```bash
curl -X PATCH http://localhost:8001/api/v1/documents/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Updated Safety Guidelines",
    "status": "active"
  }'
```

### Delete Document
```bash
curl -X DELETE http://localhost:8001/api/v1/documents/1 \
  -H "Authorization: Bearer $TOKEN"
```

---

## Versions

### List Versions
```bash
curl http://localhost:8001/api/v1/documents/1/versions \
  -H "Authorization: Bearer $TOKEN"
```

### Create Version
```bash
curl -X POST http://localhost:8001/api/v1/documents/1/versions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "# Safety Guidelines\n\n## Introduction\n\nThis document outlines..."
  }'
```

### Publish Version
```bash
curl -X POST http://localhost:8001/api/v1/versions/1/publish \
  -H "Authorization: Bearer $TOKEN"
```

### Delete Version (unpublished only)
```bash
curl -X DELETE http://localhost:8001/api/v1/versions/1 \
  -H "Authorization: Bearer $TOKEN"
```

---

## Attachments

### List Attachments
```bash
curl http://localhost:8001/api/v1/documents/1/attachments \
  -H "Authorization: Bearer $TOKEN"
```

### Upload Attachment
```bash
curl -X POST http://localhost:8001/api/v1/documents/1/attachments \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/document.docx"
```

### Download Attachment
```bash
curl http://localhost:8001/api/v1/attachments/1/download \
  -H "Authorization: Bearer $TOKEN" \
  -o downloaded_file.docx
```

### Delete Attachment
```bash
curl -X DELETE http://localhost:8001/api/v1/attachments/1 \
  -H "Authorization: Bearer $TOKEN"
```

---

## Comments

### List Comments
```bash
curl http://localhost:8001/api/v1/documents/1/comments \
  -H "Authorization: Bearer $TOKEN"
```

### Add Comment
```bash
curl -X POST http://localhost:8001/api/v1/documents/1/comments \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "This document is very helpful!"
  }'
```

### Reply to Comment
```bash
curl -X POST http://localhost:8001/api/v1/documents/1/comments \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Thanks for the feedback!",
    "parent_id": 1
  }'
```

### Update Comment
```bash
curl -X PATCH http://localhost:8001/api/v1/comments/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Updated comment text"
  }'
```

### Delete Comment
```bash
curl -X DELETE http://localhost:8001/api/v1/comments/1 \
  -H "Authorization: Bearer $TOKEN"
```

---

## Search

### Full-Text Search
```bash
curl "http://localhost:8001/api/v1/search/?q=safety" \
  -H "Authorization: Bearer $TOKEN"
```

### Search with Filters
```bash
curl "http://localhost:8001/api/v1/search/?q=policy&category=hr" \
  -H "Authorization: Bearer $TOKEN"
```

### Saved Searches

#### List Saved Searches
```bash
curl http://localhost:8001/api/v1/search/saved \
  -H "Authorization: Bearer $TOKEN"
```

#### Create Saved Search
```bash
curl -X POST http://localhost:8001/api/v1/search/saved \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "HR Policies",
    "query": "policy",
    "category": "hr"
  }'
```

#### Run Saved Search
```bash
curl http://localhost:8001/api/v1/search/saved/1/run \
  -H "Authorization: Bearer $TOKEN"
```

---

## Engagement

### Bookmarks

#### List Bookmarks
```bash
curl http://localhost:8001/api/v1/engagement/bookmarks \
  -H "Authorization: Bearer $TOKEN"
```

#### Add Bookmark
```bash
curl -X POST http://localhost:8001/api/v1/engagement/bookmarks/1 \
  -H "Authorization: Bearer $TOKEN"
```

#### Remove Bookmark
```bash
curl -X DELETE http://localhost:8001/api/v1/engagement/bookmarks/1 \
  -H "Authorization: Bearer $TOKEN"
```

### Feedback

#### Submit Feedback
```bash
curl -X POST http://localhost:8001/api/v1/engagement/feedback/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "is_helpful": true,
    "comment": "Very clear and well-written!"
  }'
```

#### Get Feedback Stats
```bash
curl http://localhost:8001/api/v1/engagement/feedback/1/stats \
  -H "Authorization: Bearer $TOKEN"
```

### Reading Progress

#### Update Progress
```bash
curl -X PUT http://localhost:8001/api/v1/engagement/progress/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "progress_percent": 75
  }'
```

#### List Progress
```bash
curl http://localhost:8001/api/v1/engagement/progress \
  -H "Authorization: Bearer $TOKEN"
```

---

## Viewer Portal (Public - No Auth)

### List Published Documents
```bash
curl http://localhost:8001/api/v1/viewer/documents
```

### Search Documents
```bash
curl "http://localhost:8001/api/v1/viewer/documents?search=safety"
```

### Get Document Details
```bash
curl http://localhost:8001/api/v1/viewer/documents/1
```

### Get Document Versions
```bash
curl http://localhost:8001/api/v1/viewer/documents/1/versions
```

### Get Document Attachments
```bash
curl http://localhost:8001/api/v1/viewer/documents/1/attachments
```

### Get Document Comments
```bash
curl http://localhost:8001/api/v1/viewer/documents/1/comments
```

---

## Health Checks

### Basic Health
```bash
curl http://localhost:8001/health
```

### Readiness
```bash
curl http://localhost:8001/ready
```

### Detailed Health
```bash
curl http://localhost:8001/health/detailed
```

---

## Error Responses

### 401 Unauthorized
```json
{
  "detail": "Not authenticated"
}
```

### 403 Forbidden
```json
{
  "detail": "Not enough permissions"
}
```

### 404 Not Found
```json
{
  "detail": "Document not found"
}
```

### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "title"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 429 Rate Limited
```json
{
  "detail": "Too many requests. Please try again later.",
  "retry_after": 30
}
```
