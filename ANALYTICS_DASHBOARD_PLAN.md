# Analytics Dashboard Implementation Plan

## Overview

Build a comprehensive analytics dashboard that provides insights into document engagement, user activity, content production, and customer portal usage. The dashboard will have role-based views with different metrics available based on user permissions.

**Estimated Effort:** 22-33 story points (~3-4 days)

---

## Implementation Progress

| Phase | Status | Completed Date | Notes |
|-------|--------|----------------|-------|
| Phase 1: Backend Foundation | ✅ **COMPLETE** | 2026-01-23 | All endpoints, schemas, service, tests |
| Phase 2: Backend Complete | ✅ **COMPLETE** | 2026-01-23 | Merged into Phase 1 |
| Phase 3: Frontend Foundation | ✅ **COMPLETE** | 2026-01-23 | All components, hooks, pages |
| Phase 4: Frontend Complete | ✅ **COMPLETE** | 2026-01-23 | Routing, navigation added |

### Backend Files Created

| File | Lines | Description |
|------|-------|-------------|
| `app/schemas/analytics.py` | 265 | Pydantic response schemas |
| `app/services/analytics_service.py` | 815 | Analytics aggregation logic |
| `app/api/management/analytics.py` | 360 | REST API endpoints |
| `tests/test_analytics.py` | 290 | 37 unit tests |

### Frontend Files Created

| File | Description |
|------|-------------|
| `src/components/analytics/StatCard.tsx` | Reusable stat card with icon, value, trend |
| `src/components/analytics/LineChartWidget.tsx` | Time series line charts |
| `src/components/analytics/BarChartWidget.tsx` | Category bar charts |
| `src/components/analytics/PieChartWidget.tsx` | Distribution pie charts |
| `src/components/analytics/DonutChartWidget.tsx` | Donut charts with center label |
| `src/components/analytics/LeaderboardTable.tsx` | Top 10 ranking tables |
| `src/components/analytics/DateRangePicker.tsx` | Date range with presets |
| `src/components/analytics/ExportButton.tsx` | CSV/PDF export button |
| `src/components/analytics/index.ts` | Barrel export |
| `src/components/analytics/hooks/useAnalytics.ts` | React Query hooks for all endpoints |
| `src/components/analytics/sections/OverviewSection.tsx` | Overview tab content |
| `src/components/analytics/sections/EngagementSection.tsx` | Engagement analytics |
| `src/components/analytics/sections/UserSection.tsx` | User analytics (ADMIN+) |
| `src/components/analytics/sections/ContentSection.tsx` | Content production metrics |
| `src/components/analytics/sections/FeedbackSection.tsx` | Feedback analytics |
| `src/components/analytics/sections/TenantSection.tsx` | Tenant comparison (SYSTEM_ADMIN) |
| `src/pages/AnalyticsDashboardPage.tsx` | Main dashboard page with tabs |

### Files Modified

| File | Change |
|------|--------|
| `app/main.py` | Registered analytics router |
| `src/types/index.ts` | Added analytics TypeScript types |
| `src/lib/api.ts` | Added analytics API methods |
| `src/config/routes.ts` | Added /analytics route |
| `src/App.tsx` | Added analytics page route |

---

## 1. Data Sources

### Available Models for Analytics

| Model | Key Fields | Analytics Use |
|-------|------------|---------------|
| `AuditLog` | action_type, document_id, user_id, created_at, details | Views, downloads, user activity trends |
| `ReadingProgress` | document_id, user_id, progress_percentage, time_spent | Completion rates, engagement depth |
| `Feedback` | document_id, user_id, type, status, is_helpful, created_at, responded_at | Helpfulness metrics, response times |
| `Bookmark` | document_id, user_id, created_at | Popular documents, user preferences |
| `Comment` | document_id, user_id, created_at, parent_id | Discussion activity |
| `Document` | status, visibility, category_id, created_at, tenant_id | Content lifecycle |
| `Version` | document_id, is_published, published_at, created_by | Publication velocity |
| `ReviewRequest` | status, created_at, reviewed_at, reviewer_id | Review turnaround |
| `User` | role, is_active, created_at, tenant_id | User growth, distribution |
| `Invitation` | status, created_at, accepted_at | Onboarding funnel |

---

## 2. Role-Based Dashboard Views

### Access Matrix

| Dashboard Section | SYSTEM_ADMIN | ADMIN | MANAGER | EDITOR | VIEWER | CUSTOMER |
|-------------------|--------------|-------|---------|--------|--------|----------|
| Overview Stats | ✅ Global | ✅ Tenant | ✅ Tenant | ✅ Personal | ✅ Personal | ✅ Personal |
| Engagement Analytics | ✅ Global | ✅ Tenant | ✅ Team | ❌ | ❌ | ❌ |
| User Analytics | ✅ Global | ✅ Tenant | ❌ | ❌ | ❌ | ❌ |
| Content Production | ✅ Global | ✅ Tenant | ✅ Team | ✅ Personal | ❌ | ❌ |
| Feedback Analytics | ✅ Global | ✅ Tenant | ✅ Tenant | ❌ | ❌ | ❌ |
| Tenant Comparison | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Export Reports | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |

---

## 3. Dashboard Sections & Widgets

### 3.1 Overview Dashboard (All Internal Users)

| Widget | Data Source | Type | Description |
|--------|-------------|------|-------------|
| Total Documents | Document.count() | Number Card | Total docs in scope |
| Documents by Status | Document.group_by(status) | Donut Chart | Draft/Active/Archived breakdown |
| Documents by Category | Document.group_by(category) | Bar Chart | Horizontal bars by category |
| Recent Activity | AuditLog (last 7 days) | Activity Feed | Last 10 actions |
| Pending Reviews | ReviewRequest.filter(PENDING) | Badge Count | Action required indicator |
| Quick Stats | Multiple | Stat Cards Row | Views today, new docs this week |

### 3.2 Engagement Analytics (Admin/Manager)

| Widget | Data Source | Type | Description |
|--------|-------------|------|-------------|
| Views Over Time | AuditLog(VIEW) by date | Line Chart | Daily/Weekly/Monthly toggle |
| Downloads Over Time | AuditLog(DOWNLOAD) by date | Line Chart | Trend analysis |
| Top 10 Viewed Documents | AuditLog(VIEW) grouped | Leaderboard Table | Most popular content |
| Top 10 Downloaded Documents | AuditLog(DOWNLOAD) grouped | Leaderboard Table | Most downloaded |
| Average Reading Progress | ReadingProgress.avg() | Gauge | Overall completion % |
| Completion Rate | ReadingProgress(100%) / total | Percentage Card | Fully read documents |
| Time Spent Reading | ReadingProgress.sum(time) | Duration Card | Total engagement time |
| Unique Visitors | AuditLog.distinct(user_id) | Number Card | Unique users viewing docs |

### 3.3 User Analytics (Admin Only)

| Widget | Data Source | Type | Description |
|--------|-------------|------|-------------|
| Users by Role | User.group_by(role) | Pie Chart | Role distribution |
| Active vs Inactive | User.group_by(is_active) | Donut Chart | Account status |
| New Registrations | User.group_by(created_at) | Area Chart | Growth over time |
| Most Active Users | AuditLog.group_by(user_id) | Top 10 Table | Power users |
| Login Activity | (if tracked) | Heatmap | Activity by day/hour |
| Invitation Funnel | Invitation by status | Funnel Chart | Sent → Accepted → Active |

### 3.4 Content Production (Manager/Editor)

| Widget | Data Source | Type | Description |
|--------|-------------|------|-------------|
| Documents Created | Document.group_by(created_at) | Area Chart | Production over time |
| Versions Published | Version(published) by date | Line Chart | Publication velocity |
| Review Turnaround | ReviewRequest avg(reviewed_at - created_at) | Duration Card | Avg approval time |
| Approval Rate | ReviewRequest(APPROVED) / total | Percentage | Success rate |
| Pending vs Completed | ReviewRequest by status | Stacked Bar | Review pipeline |
| Comments Activity | Comment.count() by date | Line Chart | Discussion trends |
| My Contributions | (for EDITOR) | Personal Stats | Docs, versions, comments |

### 3.5 Feedback Analytics (Admin/Manager)

| Widget | Data Source | Type | Description |
|--------|-------------|------|-------------|
| Feedback by Type | Feedback.group_by(type) | Pie Chart | Question/Suggestion/Issue/Other |
| Feedback by Status | Feedback.group_by(status) | Stacked Bar | Pending/Responded/Closed |
| Feedback Over Time | Feedback.group_by(created_at) | Line Chart | Volume trends |
| Average Response Time | Feedback avg(responded_at - created_at) | Duration Card | Response SLA |
| Helpfulness Score | (helpful / total) * 100 | Percentage Gauge | Content quality indicator |
| Top Feedback Documents | Feedback.group_by(document_id) | Table | Most discussed docs |
| Unresolved Feedback | Feedback.filter(PENDING) | Count + List | Action required |

### 3.6 Tenant Comparison (System Admin Only)

| Widget | Data Source | Type | Description |
|--------|-------------|------|-------------|
| Tenants Overview | Tenant with counts | Summary Cards | Active tenants, total users |
| Per-Tenant Metrics | Aggregated by tenant_id | Comparison Table | Docs, users, activity per tenant |
| Tenant Activity Trend | AuditLog by tenant by date | Multi-line Chart | Compare tenant engagement |
| Tenant Health Score | Composite metric | Scorecard | Active users %, content freshness |

---

## 4. Time Granularity

### Aggregation Levels

| Granularity | Use Case | Date Format | Max Range |
|-------------|----------|-------------|-----------|
| **Daily** | Last 7-30 days detail | YYYY-MM-DD | 90 days |
| **Weekly** | Last 3-6 months trends | YYYY-WXX | 52 weeks |
| **Monthly** | Year-over-year analysis | YYYY-MM | 24 months |

### Implementation

```python
class TimeGranularity(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"

def get_date_trunc(granularity: TimeGranularity, column):
    """SQLAlchemy date truncation based on granularity"""
    if granularity == TimeGranularity.DAILY:
        return func.date(column)
    elif granularity == TimeGranularity.WEEKLY:
        return func.strftime('%Y-W%W', column)  # SQLite
        # PostgreSQL: func.date_trunc('week', column)
    elif granularity == TimeGranularity.MONTHLY:
        return func.strftime('%Y-%m', column)  # SQLite
        # PostgreSQL: func.date_trunc('month', column)
```

### Default Granularity by Range

| Selected Range | Default Granularity |
|----------------|---------------------|
| Last 7 days | Daily |
| Last 30 days | Daily |
| Last 90 days | Weekly |
| Last 6 months | Weekly |
| Last 12 months | Monthly |
| Custom | Auto-detect based on span |

---

## 5. Caching Strategy

### Approach: React Query + Optional Redis

**Frontend (React Query):**
- `staleTime: 5 minutes` for dashboard stats
- `staleTime: 1 minute` for real-time widgets
- Background refetch on window focus

**Backend (Optional Redis):**
- Cache expensive aggregations with 5-minute TTL
- Key pattern: `analytics:{tenant_id}:{endpoint}:{params_hash}`
- Invalidate on data changes (via signals/events)

### Cache Configuration

```python
# app/config.py
ANALYTICS_CACHE_TTL = 300  # 5 minutes
ANALYTICS_CACHE_ENABLED = True  # Set False for development

# Cache keys
def get_cache_key(tenant_id: int, endpoint: str, params: dict) -> str:
    params_hash = hashlib.md5(json.dumps(params, sort_keys=True).encode()).hexdigest()[:8]
    return f"analytics:{tenant_id or 'global'}:{endpoint}:{params_hash}"
```

### MVP Approach (No Redis)
Start without Redis caching. Use:
1. Database query optimization with proper indexes
2. React Query caching on frontend
3. Add Redis later if performance issues arise

---

## 6. Export Functionality

### Supported Formats

| Format | Library | Use Case |
|--------|---------|----------|
| **CSV** | Built-in Python `csv` | Data export for Excel/analysis |
| **PDF** | `reportlab` or `weasyprint` | Printable reports |

### Export Endpoints

```python
# CSV Export
GET /api/v1/analytics/export/csv?report={report_type}&date_from=&date_to=

# PDF Export  
GET /api/v1/analytics/export/pdf?report={report_type}&date_from=&date_to=
```

### Report Types

| Report Type | Contents | Available To |
|-------------|----------|--------------|
| `overview` | Summary stats, document counts | Admin+ |
| `engagement` | Views, downloads, reading progress | Admin+ |
| `users` | User list with activity metrics | Admin |
| `content` | Document production stats | Manager+ |
| `feedback` | Feedback summary and details | Manager+ |
| `tenant-comparison` | Cross-tenant metrics | System Admin |

### CSV Implementation

```python
import csv
from io import StringIO
from fastapi.responses import StreamingResponse

@router.get("/export/csv")
async def export_csv(
    report: str,
    date_from: date,
    date_to: date,
    tenant_ctx: TenantContext = Depends(require_manager),
    db: Session = Depends(get_db)
):
    data = get_report_data(report, date_from, date_to, tenant_ctx, db)
    
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={report}_{date_to}.csv"}
    )
```

### PDF Implementation

```python
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO

@router.get("/export/pdf")
async def export_pdf(
    report: str,
    date_from: date,
    date_to: date,
    tenant_ctx: TenantContext = Depends(require_manager),
    db: Session = Depends(get_db)
):
    data = get_report_data(report, date_from, date_to, tenant_ctx, db)
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    
    # Add title
    styles = getSampleStyleSheet()
    elements.append(Paragraph(f"Analytics Report: {report}", styles['Title']))
    elements.append(Paragraph(f"Period: {date_from} to {date_to}", styles['Normal']))
    
    # Add table
    table_data = [list(data[0].keys())] + [list(row.values()) for row in data]
    table = Table(table_data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(table)
    
    doc.build(elements)
    buffer.seek(0)
    
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={report}_{date_to}.pdf"}
    )
```

---

## 7. API Endpoints

### Backend API Structure

```
/api/v1/analytics/
├── overview                    GET - Summary stats
├── engagement                  GET - Views, downloads, reading metrics
├── engagement/top-documents    GET - Most viewed/downloaded
├── users                       GET - User metrics and distribution
├── users/activity              GET - User activity details
├── content                     GET - Production metrics
├── content/reviews             GET - Review pipeline stats
├── feedback                    GET - Feedback metrics
├── tenants                     GET - Cross-tenant comparison (System Admin)
├── export/csv                  GET - CSV export
└── export/pdf                  GET - PDF export
```

### Common Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `date_from` | date | 30 days ago | Start of period |
| `date_to` | date | today | End of period |
| `granularity` | enum | auto | daily/weekly/monthly |
| `tenant_id` | int | from context | Filter by tenant (System Admin) |

### Response Schemas

```python
# schemas/analytics.py

class TimeSeriesPoint(BaseModel):
    date: str  # ISO format or week/month format
    value: int

class DocumentStats(BaseModel):
    document_id: int
    document_number: str
    title: str
    view_count: int
    download_count: int

class AnalyticsOverview(BaseModel):
    period_start: date
    period_end: date
    total_documents: int
    total_users: int
    total_views: int
    total_downloads: int
    documents_by_status: dict[str, int]
    documents_by_category: list[dict]
    pending_reviews: int

class EngagementAnalytics(BaseModel):
    views_over_time: list[TimeSeriesPoint]
    downloads_over_time: list[TimeSeriesPoint]
    unique_visitors: int
    avg_reading_progress: float
    completion_rate: float
    total_time_spent_minutes: int

class TopDocuments(BaseModel):
    by_views: list[DocumentStats]
    by_downloads: list[DocumentStats]

class UserAnalytics(BaseModel):
    total_users: int
    active_users: int
    users_by_role: dict[str, int]
    new_users_over_time: list[TimeSeriesPoint]
    most_active_users: list[dict]

class ContentAnalytics(BaseModel):
    documents_created_over_time: list[TimeSeriesPoint]
    versions_published_over_time: list[TimeSeriesPoint]
    avg_review_turnaround_hours: float
    approval_rate: float
    reviews_by_status: dict[str, int]

class FeedbackAnalytics(BaseModel):
    total_feedback: int
    feedback_by_type: dict[str, int]
    feedback_by_status: dict[str, int]
    feedback_over_time: list[TimeSeriesPoint]
    avg_response_time_hours: float
    helpfulness_rate: float

class TenantMetrics(BaseModel):
    tenant_id: int
    tenant_name: str
    total_documents: int
    total_users: int
    active_users_30d: int
    total_views_30d: int
    health_score: float  # 0-100
```

---

## 8. Frontend Components

### Charting Library: Recharts

```bash
npm install recharts
```

### Component Structure

```
src/
├── pages/
│   └── AnalyticsDashboardPage.tsx
├── components/
│   └── analytics/
│       ├── index.ts                 # Barrel export
│       ├── StatCard.tsx             # Reusable number card
│       ├── LineChartWidget.tsx      # Time series chart
│       ├── BarChartWidget.tsx       # Category comparison
│       ├── PieChartWidget.tsx       # Distribution chart
│       ├── DonutChartWidget.tsx     # Status breakdown
│       ├── LeaderboardTable.tsx     # Top 10 rankings
│       ├── ActivityFeed.tsx         # Recent actions list
│       ├── DateRangePicker.tsx      # Period selector
│       ├── GranularityToggle.tsx    # Daily/Weekly/Monthly
│       ├── ExportButton.tsx         # CSV/PDF download
│       │
│       ├── sections/
│       │   ├── OverviewSection.tsx
│       │   ├── EngagementSection.tsx
│       │   ├── UserSection.tsx
│       │   ├── ContentSection.tsx
│       │   ├── FeedbackSection.tsx
│       │   └── TenantSection.tsx
│       │
│       └── hooks/
│           ├── useAnalyticsOverview.ts
│           ├── useEngagementAnalytics.ts
│           ├── useUserAnalytics.ts
│           ├── useContentAnalytics.ts
│           ├── useFeedbackAnalytics.ts
│           └── useTenantAnalytics.ts
├── lib/
│   └── api.ts                       # Add analytics endpoints
```

### Key Components

#### StatCard.tsx
```tsx
interface StatCardProps {
  title: string;
  value: number | string;
  icon: LucideIcon;
  trend?: { value: number; isPositive: boolean };
  subtitle?: string;
}

export function StatCard({ title, value, icon: Icon, trend, subtitle }: StatCardProps) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-500">{title}</p>
          <p className="text-2xl font-bold text-gray-900">{value}</p>
          {subtitle && <p className="text-xs text-gray-400">{subtitle}</p>}
        </div>
        <div className="p-3 bg-blue-50 rounded-full">
          <Icon className="w-6 h-6 text-blue-600" />
        </div>
      </div>
      {trend && (
        <div className={`mt-2 text-sm ${trend.isPositive ? 'text-green-600' : 'text-red-600'}`}>
          {trend.isPositive ? '↑' : '↓'} {Math.abs(trend.value)}% vs previous period
        </div>
      )}
    </div>
  );
}
```

#### LineChartWidget.tsx
```tsx
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface LineChartWidgetProps {
  title: string;
  data: { date: string; value: number }[];
  color?: string;
  height?: number;
}

export function LineChartWidget({ title, data, color = '#3B82F6', height = 300 }: LineChartWidgetProps) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-medium text-gray-900 mb-4">{title}</h3>
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis />
          <Tooltip />
          <Line type="monotone" dataKey="value" stroke={color} strokeWidth={2} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
```

---

## 9. Implementation Steps

### Phase 1: Backend Foundation (Day 1) ✅ COMPLETE

| Task | File | Priority | Status |
|------|------|----------|--------|
| Create analytics schemas | `app/schemas/analytics.py` | P0 | ✅ Done |
| Create AnalyticsService class | `app/services/analytics_service.py` | P0 | ✅ Done |
| Implement overview endpoint | `app/api/management/analytics.py` | P0 | ✅ Done |
| Implement engagement endpoint | `app/api/management/analytics.py` | P0 | ✅ Done |
| Add date range filtering | Service layer | P0 | ✅ Done |
| Write unit tests | `tests/test_analytics.py` | P1 | ✅ Done (37 tests) |

### Phase 2: Backend Complete (Day 2) ✅ COMPLETE (Merged into Phase 1)

| Task | File | Priority | Status |
|------|------|----------|--------|
| Implement user analytics | `app/api/management/analytics.py` | P0 | ✅ Done |
| Implement content analytics | `app/api/management/analytics.py` | P0 | ✅ Done |
| Implement feedback analytics | `app/api/management/analytics.py` | P0 | ✅ Done |
| Implement tenant comparison | `app/api/management/analytics.py` | P1 | ✅ Done |
| Add CSV export | `app/api/management/analytics.py` | P1 | ✅ Done |
| Add PDF export | `app/api/management/analytics.py` | P1 | ✅ Done |
| Add granularity support | Service layer | P1 | ✅ Done |

### Phase 3: Frontend Foundation (Day 3) ⏳ NOT STARTED

| Task | File | Priority | Status |
|------|------|----------|--------|
| Install Recharts | `package.json` | P0 | ⏳ |
| Create StatCard component | `components/analytics/StatCard.tsx` | P0 | ⏳ |
| Create chart components | `components/analytics/*.tsx` | P0 | ⏳ |
| Add API methods | `lib/api.ts` | P0 | ⏳ |
| Create React Query hooks | `components/analytics/hooks/*.ts` | P0 | ⏳ |
| Build OverviewSection | `components/analytics/sections/` | P0 | ⏳ |

### Phase 4: Frontend Complete (Day 4) ⏳ NOT STARTED

| Task | File | Priority | Status |
|------|------|----------|--------|
| Build EngagementSection | `components/analytics/sections/` | P0 | ⏳ |
| Build UserSection | `components/analytics/sections/` | P0 | ⏳ |
| Build ContentSection | `components/analytics/sections/` | P1 | ⏳ |
| Build FeedbackSection | `components/analytics/sections/` | P1 | ⏳ |
| Build TenantSection | `components/analytics/sections/` | P1 | ⏳ |
| Add DateRangePicker | `components/analytics/` | P1 | ⏳ |
| Add ExportButton | `components/analytics/` | P1 | ⏳ |
| Add navigation/routing | `App.tsx`, sidebar | P0 | ⏳ |
| Role-based section visibility | Dashboard page | P0 | ⏳ |

---

## 10. Database Indexes

Add indexes for analytics query performance:

```python
# migrations/add_analytics_indexes.py

from alembic import op

def upgrade():
    # AuditLog indexes for time-series queries
    op.create_index('ix_audit_logs_action_created', 'audit_logs', ['action_type', 'created_at'])
    op.create_index('ix_audit_logs_document_action', 'audit_logs', ['document_id', 'action_type'])
    op.create_index('ix_audit_logs_tenant_created', 'audit_logs', ['tenant_id', 'created_at'])
    
    # ReadingProgress indexes
    op.create_index('ix_reading_progress_document', 'reading_progress', ['document_id'])
    
    # Feedback indexes
    op.create_index('ix_feedback_created', 'feedback', ['created_at'])
    op.create_index('ix_feedback_status', 'feedback', ['status'])
    
    # Document indexes
    op.create_index('ix_documents_tenant_status', 'documents', ['tenant_id', 'status'])
    op.create_index('ix_documents_created', 'documents', ['created_at'])

def downgrade():
    op.drop_index('ix_audit_logs_action_created')
    op.drop_index('ix_audit_logs_document_action')
    op.drop_index('ix_audit_logs_tenant_created')
    op.drop_index('ix_reading_progress_document')
    op.drop_index('ix_feedback_created')
    op.drop_index('ix_feedback_status')
    op.drop_index('ix_documents_tenant_status')
    op.drop_index('ix_documents_created')
```

---

## 11. Testing Strategy

### Backend Tests

```python
# tests/test_analytics.py

class TestAnalyticsOverview:
    def test_overview_returns_correct_counts(self, db, tenant1_context)
    def test_overview_filters_by_tenant(self, db, tenant1_context, tenant2_data)
    def test_overview_system_admin_sees_all(self, db, system_admin_context)
    def test_overview_respects_date_range(self, db, tenant1_context)

class TestEngagementAnalytics:
    def test_views_over_time_daily(self, db, tenant1_context)
    def test_views_over_time_weekly(self, db, tenant1_context)
    def test_views_over_time_monthly(self, db, tenant1_context)
    def test_top_documents_ordered_correctly(self, db, tenant1_context)
    def test_reading_progress_calculation(self, db, tenant1_context)

class TestUserAnalytics:
    def test_users_by_role_distribution(self, db, admin_context)
    def test_new_users_over_time(self, db, admin_context)
    def test_requires_admin_role(self, db, editor_context)

class TestExport:
    def test_csv_export_format(self, db, admin_context)
    def test_pdf_export_generates_file(self, db, admin_context)
    def test_export_respects_tenant_filter(self, db, tenant1_context)
```

### Frontend Tests

```typescript
// e2e/analytics.spec.ts

test.describe('Analytics Dashboard', () => {
  test('admin sees all sections', async ({ page }) => {
    await loginAsAdmin(page);
    await page.goto('/analytics');
    await expect(page.locator('[data-testid="overview-section"]')).toBeVisible();
    await expect(page.locator('[data-testid="engagement-section"]')).toBeVisible();
    await expect(page.locator('[data-testid="user-section"]')).toBeVisible();
  });

  test('editor sees limited sections', async ({ page }) => {
    await loginAsEditor(page);
    await page.goto('/analytics');
    await expect(page.locator('[data-testid="overview-section"]')).toBeVisible();
    await expect(page.locator('[data-testid="user-section"]')).not.toBeVisible();
  });

  test('date range filter updates charts', async ({ page }) => {
    await loginAsAdmin(page);
    await page.goto('/analytics');
    await page.click('[data-testid="date-range-picker"]');
    await page.click('text=Last 7 days');
    await expect(page.locator('[data-testid="views-chart"]')).toBeVisible();
  });

  test('csv export downloads file', async ({ page }) => {
    await loginAsAdmin(page);
    await page.goto('/analytics');
    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.click('[data-testid="export-csv"]'),
    ]);
    expect(download.suggestedFilename()).toContain('.csv');
  });
});
```

---

## 12. Dependencies

### Backend

```txt
# requirements.txt additions
reportlab>=4.0.0  # PDF generation
```

### Frontend

```json
// package.json additions
{
  "dependencies": {
    "recharts": "^2.12.0",
    "date-fns": "^3.0.0"  // Already installed
  }
}
```

---

## 13. Success Criteria

| Metric | Target |
|--------|--------|
| Page load time | < 2 seconds |
| Chart render time | < 500ms |
| API response time | < 1 second (p95) |
| Test coverage | > 80% for analytics module |
| All role-based views | Working correctly |
| Export functionality | CSV and PDF working |
| Mobile responsiveness | Charts readable on tablet+ |

---

## 14. Future Enhancements

1. **Real-time updates** - WebSocket for live dashboard
2. **Custom date ranges** - Calendar picker for arbitrary ranges
3. **Saved reports** - Save filter configurations
4. **Scheduled exports** - Email reports on schedule
5. **Comparison mode** - Compare two time periods
6. **Drill-down** - Click chart to see details
7. **Custom dashboards** - User-configurable widget layout
8. **Alerts** - Threshold-based notifications

---

## 15. File Checklist

### Backend Files to Create

- [x] `app/schemas/analytics.py` ✅ Created (265 lines)
- [x] `app/services/analytics_service.py` ✅ Created (815 lines)
- [x] `app/api/management/analytics.py` ✅ Created (360 lines)
- [x] `tests/test_analytics.py` ✅ Created (290 lines, 37 tests)
- [ ] `migrations/add_analytics_indexes.py` (optional - defer until needed)

### Frontend Files to Create

- [x] `src/components/analytics/StatCard.tsx` ✅
- [x] `src/components/analytics/LineChartWidget.tsx` ✅
- [x] `src/components/analytics/BarChartWidget.tsx` ✅
- [x] `src/components/analytics/PieChartWidget.tsx` ✅
- [x] `src/components/analytics/DonutChartWidget.tsx` ✅
- [x] `src/components/analytics/LeaderboardTable.tsx` ✅
- [x] `src/components/analytics/DateRangePicker.tsx` ✅
- [x] `src/components/analytics/ExportButton.tsx` ✅
- [x] `src/components/analytics/index.ts` ✅ (barrel export)
- [x] `src/components/analytics/sections/OverviewSection.tsx` ✅
- [x] `src/components/analytics/sections/EngagementSection.tsx` ✅
- [x] `src/components/analytics/sections/UserSection.tsx` ✅
- [x] `src/components/analytics/sections/ContentSection.tsx` ✅
- [x] `src/components/analytics/sections/FeedbackSection.tsx` ✅
- [x] `src/components/analytics/sections/TenantSection.tsx` ✅
- [x] `src/components/analytics/hooks/useAnalytics.ts` ✅
- [x] `src/pages/AnalyticsDashboardPage.tsx` ✅
- [ ] `e2e/analytics.spec.ts` (optional - E2E tests)

### Files to Modify

- [x] `app/main.py` - Register analytics router ✅ Done
- [x] `frontend/src/lib/api.ts` - Add analytics API methods ✅ Done
- [x] `frontend/src/types/index.ts` - Add analytics types ✅ Done
- [x] `frontend/src/App.tsx` - Add analytics route ✅ Done
- [x] `frontend/src/config/routes.ts` - Add analytics nav item ✅ Done
- [x] `package.json` - Add recharts ✅ Done
- [x] `requirements.txt` - Add reportlab ✅ Done

---

## 16. Backend Implementation Details (Completed)

### API Endpoints Implemented

| Endpoint | Method | Permission | Description |
|----------|--------|------------|-------------|
| `/analytics/overview` | GET | MANAGER+ | Summary stats, document counts |
| `/analytics/recent-activity` | GET | MANAGER+ | Activity feed (limit param) |
| `/analytics/engagement` | GET | MANAGER+ | Views/downloads over time |
| `/analytics/engagement/top-documents` | GET | MANAGER+ | Leaderboards |
| `/analytics/users` | GET | ADMIN | User metrics and distribution |
| `/analytics/content` | GET | MANAGER+ | Production metrics |
| `/analytics/feedback` | GET | MANAGER+ | Feedback metrics |
| `/analytics/tenants` | GET | SYSTEM_ADMIN | Cross-tenant comparison |
| `/analytics/export/csv` | GET | MANAGER+ | CSV download |
| `/analytics/export/pdf` | GET | MANAGER+ | PDF download (requires reportlab) |

### AnalyticsService Methods

```python
class AnalyticsService:
    def get_overview(date_from, date_to) -> AnalyticsOverview
    def get_recent_activity(limit) -> List[RecentActivity]
    def get_engagement(date_from, date_to, granularity) -> EngagementAnalytics
    def get_top_documents(date_from, date_to, limit) -> TopDocuments
    def get_user_analytics(date_from, date_to, granularity) -> UserAnalytics
    def get_content_analytics(date_from, date_to, granularity) -> ContentAnalytics
    def get_feedback_analytics(date_from, date_to, granularity) -> FeedbackAnalytics
    def get_tenant_analytics(date_from, date_to) -> TenantAnalytics
```

### Test Coverage

- **37 unit tests** covering:
  - All permission levels (ADMIN, MANAGER, EDITOR, VIEWER, CUSTOMER)
  - Date range filtering
  - Granularity parameters
  - CSV/PDF export
  - Data integrity validation
  - Response schema validation
