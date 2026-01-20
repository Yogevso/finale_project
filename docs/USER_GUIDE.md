# V2 Document Portal - User Guide

## Quick Start

### Default Login Credentials
| Username | Password | Role | Access |
|----------|----------|------|--------|
| admin | admin123 | Admin | Full access to everything |
| editor | editor123 | Editor | Create/edit documents |
| viewer | viewer123 | Viewer | Read-only access |

### Accessing the Portal
- **Management Portal**: http://localhost:3000 (requires login)
- **Viewer Portal**: http://localhost:3000/viewer (public access)
- **API Documentation**: http://localhost:8001/docs

---

## Management Portal

### Dashboard
The dashboard shows key metrics at a glance:
- Total documents
- Active documents
- Draft documents
- Recent activity

### Documents

#### Creating a Document
1. Click **"New Document"** button
2. Fill in required fields:
   - **Title**: Document name
   - **Document Number**: Unique identifier (auto-generated or custom)
   - **Description**: Brief summary
   - **Category**: Optional categorization
3. Click **"Create"**

#### Document Statuses
| Status | Meaning |
|--------|---------|
| Draft | Work in progress, not publicly visible |
| Active | Published and visible in Viewer Portal |
| Archived | Hidden from normal views, preserved for records |

#### Editing a Document
1. Navigate to document list
2. Click on document title or **"Edit"** button
3. Modify fields as needed
4. Click **"Save Changes"**

#### Deleting a Document
1. Open document detail page
2. Click **"Delete"** button
3. Confirm deletion in popup

### Versions

#### Understanding Versions
- Documents support multiple versions
- Only one version can be "published" at a time
- Published versions are immutable (cannot be edited)
- Unpublished versions can be edited freely

#### Creating a Version
1. Open document detail page
2. Go to **"Versions"** tab
3. Click **"New Version"**
4. Enter version content (supports Markdown)
5. Click **"Save"**

#### Publishing a Version
1. In Versions tab, find unpublished version
2. Click **"Publish"** button
3. Version becomes immutable and visible in Viewer Portal

### Attachments

#### Uploading Files
1. Open document detail page
2. Go to **"Attachments"** tab
3. Click **"Upload"** or drag-and-drop files
4. Maximum file size: 10MB

#### Supported File Types
- Documents: PDF, DOC, DOCX, XLS, XLSX, PPT, PPTX
- Images: JPG, PNG, GIF, SVG
- Text: TXT, MD, CSV
- Archives: ZIP

#### Downloading Attachments
- Click attachment name or download icon

### Comments

#### Adding Comments
1. Open document detail page
2. Go to **"Comments"** tab
3. Type comment in text area
4. Click **"Post Comment"**

#### Replying to Comments
1. Find existing comment
2. Click **"Reply"**
3. Type reply
4. Click **"Post Reply"**

#### Editing/Deleting Comments
- Edit: Click edit icon (pencil) on your comment
- Delete: Click delete icon (trash) on your comment
- Note: Only comment author can edit/delete

---

## Viewer Portal

The Viewer Portal provides public, read-only access to published documents.

### Browsing Documents
- View all active documents on the home page
- Documents are sorted by most recently updated

### Searching
1. Use search bar at top of page
2. Enter keywords
3. Results update automatically
4. Search looks in titles and descriptions

### Filtering by Category
1. Use category dropdown
2. Select desired category
3. Document list filters accordingly

### Viewing Document Details
1. Click on document card
2. View:
   - Document content (latest published version)
   - Previous versions (read-only)
   - Attachments (downloadable)
   - Comments (read-only)

### Downloading Attachments
- Click attachment name to download
- No login required

---

## Engagement Features

### Bookmarks
Save documents for quick access later:
1. Open document in Viewer Portal
2. Click **"Bookmark"** button
3. Access bookmarks from dashboard

### Feedback
Help improve documents:
1. Open document
2. Click **"Helpful"** or **"Not Helpful"**
3. Optionally add a comment

### Reading Progress
Track your reading:
- Progress is automatically saved as you scroll
- View "In Progress" and "Completed" documents in dashboard

---

## Search Features

### Basic Search
- Enter keywords in search bar
- Results ranked by relevance

### Advanced Filters
- **Category**: Filter by document category
- **Date Range**: Filter by creation/update date
- **Status**: Filter by document status (management only)

### Saved Searches
Save frequently used searches:
1. Perform a search
2. Click **"Save Search"**
3. Enter a name
4. Access from **"Saved Searches"** in sidebar

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl + K` | Focus search bar |
| `Ctrl + N` | New document (management) |
| `Esc` | Close modal/dialog |

---

## Troubleshooting

### Can't Log In
1. Check username/password
2. Caps Lock off?
3. Try resetting password (if enabled)

### Document Not Showing in Viewer
1. Check document status is **"Active"**
2. Ensure at least one version is **published**

### File Upload Fails
1. Check file size (max 10MB)
2. Check file type is supported
3. Try smaller file or different format

### Search Returns No Results
1. Check spelling
2. Try fewer/different keywords
3. Remove filters

---

## Getting Help

- **API Docs**: http://localhost:8001/docs
- **README**: See project root
- **GitHub Issues**: Report bugs and request features
