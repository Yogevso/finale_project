BEGIN TRANSACTION;
CREATE TABLE alembic_version (
	version_num VARCHAR(32) NOT NULL, 
	CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);
INSERT INTO "alembic_version" VALUES('20260227_0006');
CREATE TABLE attachment_artifacts (
	id INTEGER NOT NULL, 
	attachment_id INTEGER NOT NULL, 
	kind VARCHAR(40) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	mime_type VARCHAR(100), 
	storage_key VARCHAR(500), 
	size_bytes INTEGER, 
	sha256 VARCHAR(64), 
	content_text TEXT, 
	content_json TEXT, 
	source VARCHAR(40), 
	error TEXT, 
	generated_at DATETIME, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_attachment_artifacts_attachment_kind UNIQUE (attachment_id, kind), 
	FOREIGN KEY(attachment_id) REFERENCES attachments (id)
);
CREATE TABLE attachment_conversion_jobs (
	id INTEGER NOT NULL, 
	attachment_id INTEGER NOT NULL, 
	job_type VARCHAR(40) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	force BOOLEAN NOT NULL, 
	attempts INTEGER NOT NULL, 
	max_attempts INTEGER NOT NULL, 
	last_error TEXT, 
	started_at DATETIME, 
	finished_at DATETIME, 
	next_run_at DATETIME, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_attachment_conversion_job UNIQUE (attachment_id, job_type), 
	FOREIGN KEY(attachment_id) REFERENCES attachments (id)
);
CREATE TABLE attachments (
	id INTEGER NOT NULL, 
	document_id INTEGER NOT NULL, 
	filename VARCHAR(255) NOT NULL, 
	original_filename VARCHAR(255) NOT NULL, 
	file_size INTEGER NOT NULL, 
	size_bytes INTEGER, 
	mime_type VARCHAR(100) NOT NULL, 
	storage_path VARCHAR(500) NOT NULL, 
	storage_key VARCHAR(500), 
	sha256 VARCHAR(64), 
	preview_pdf_status VARCHAR(20), 
	preview_pdf_storage_key VARCHAR(500), 
	preview_pdf_mime_type VARCHAR(100), 
	preview_pdf_size_bytes INTEGER, 
	preview_pdf_sha256 VARCHAR(64), 
	preview_pdf_error TEXT, 
	preview_pdf_generated_at DATETIME, 
	reader_html_status VARCHAR(20), 
	reader_html_content TEXT, 
	reader_toc_json TEXT, 
	reader_toc_source VARCHAR(20), 
	reader_html_error TEXT, 
	reader_html_generated_at DATETIME, 
	uploaded_by INTEGER NOT NULL, 
	uploaded_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(document_id) REFERENCES documents (id), 
	FOREIGN KEY(uploaded_by) REFERENCES users (id)
);
CREATE TABLE audit_logs (
	id INTEGER NOT NULL, 
	user_id INTEGER, 
	document_id INTEGER, 
	action VARCHAR(8) NOT NULL, 
	details TEXT, 
	ip_address VARCHAR(45), 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(document_id) REFERENCES documents (id)
);
CREATE TABLE bookmarks (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	document_id INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(document_id) REFERENCES documents (id)
);
CREATE TABLE collaboration_activities (
	id INTEGER NOT NULL, 
	document_id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	session_id VARCHAR(100), 
	activity_type VARCHAR(17) NOT NULL, 
	details TEXT, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(document_id) REFERENCES documents (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);
CREATE TABLE collaboration_sessions (
	id INTEGER NOT NULL, 
	document_id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	session_id VARCHAR(100) NOT NULL, 
	started_at DATETIME NOT NULL, 
	ended_at DATETIME, 
	is_active BOOLEAN NOT NULL, 
	edits_count INTEGER NOT NULL, 
	last_activity_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(document_id) REFERENCES documents (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);
CREATE TABLE collaboration_snapshots (
	id INTEGER NOT NULL, 
	document_id INTEGER NOT NULL, 
	snapshot_type VARCHAR(11) NOT NULL, 
	name VARCHAR(255), 
	description TEXT, 
	yjs_state BLOB NOT NULL, 
	html_content TEXT, 
	state_size INTEGER NOT NULL, 
	created_by INTEGER, 
	session_id VARCHAR(100), 
	created_at DATETIME NOT NULL, 
	is_pinned BOOLEAN NOT NULL, 
	expires_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(document_id) REFERENCES documents (id), 
	FOREIGN KEY(created_by) REFERENCES users (id)
);
CREATE TABLE comments (
	id INTEGER NOT NULL, 
	document_id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	parent_id INTEGER, 
	content TEXT NOT NULL, 
	is_private BOOLEAN NOT NULL, 
	anchor_text TEXT, 
	anchor_id VARCHAR(100), 
	is_resolved BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(document_id) REFERENCES documents (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(parent_id) REFERENCES comments (id)
);
CREATE TABLE document_company_assignments (
	document_id INTEGER NOT NULL, 
	tenant_id INTEGER NOT NULL, 
	assigned_at DATETIME, 
	assigned_by INTEGER, 
	PRIMARY KEY (document_id, tenant_id), 
	FOREIGN KEY(document_id) REFERENCES documents (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id), 
	FOREIGN KEY(assigned_by) REFERENCES users (id)
);
CREATE TABLE document_number_sequences (
	date_key VARCHAR(8) NOT NULL, 
	next_value INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (date_key)
);
CREATE TABLE documents (
	id INTEGER NOT NULL, 
	tenant_id INTEGER, 
	title VARCHAR(500) NOT NULL, 
	document_number VARCHAR(100) NOT NULL, 
	description TEXT, 
	version_label VARCHAR(50), 
	status VARCHAR(14) NOT NULL, 
	visibility VARCHAR(8) NOT NULL, 
	category VARCHAR(100), 
	topic VARCHAR(150), 
	platform VARCHAR(100), 
	platform_id INTEGER, 
	release_branch VARCHAR(100), 
	tags TEXT, 
	yjs_state BLOB, 
	created_by INTEGER NOT NULL, 
	parent_id INTEGER, 
	row_version INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id), 
	FOREIGN KEY(platform_id) REFERENCES platforms (id), 
	FOREIGN KEY(created_by) REFERENCES users (id), 
	FOREIGN KEY(parent_id) REFERENCES documents (id)
);
CREATE TABLE domain_event_outbox (
	id INTEGER NOT NULL, 
	event_type VARCHAR(120) NOT NULL, 
	event_key VARCHAR(255), 
	payload_json TEXT NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	attempts INTEGER NOT NULL, 
	max_attempts INTEGER NOT NULL, 
	next_attempt_at DATETIME, 
	last_error TEXT, 
	claimed_at DATETIME, 
	processed_at DATETIME, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
);
CREATE TABLE feedbacks (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	document_id INTEGER NOT NULL, 
	feedback_type VARCHAR(10) NOT NULL, 
	status VARCHAR(9) NOT NULL, 
	content TEXT NOT NULL, 
	response TEXT, 
	responded_by INTEGER, 
	responded_at DATETIME, 
	is_helpful BOOLEAN, 
	comment TEXT, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(document_id) REFERENCES documents (id), 
	FOREIGN KEY(responded_by) REFERENCES users (id)
);
CREATE TABLE idempotency_keys (
	id INTEGER NOT NULL, 
	idempotency_key VARCHAR(255) NOT NULL, 
	method VARCHAR(10) NOT NULL, 
	path VARCHAR(500) NOT NULL, 
	user_scope VARCHAR(64) NOT NULL, 
	user_id INTEGER, 
	request_hash VARCHAR(64) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	response_status INTEGER, 
	response_body TEXT, 
	response_content_type VARCHAR(120), 
	processing_started_at DATETIME, 
	last_error TEXT, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_idempotency_scope UNIQUE (idempotency_key, method, path, user_scope)
);
CREATE TABLE invitations (
	id INTEGER NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	token VARCHAR(255) NOT NULL, 
	role VARCHAR(12) NOT NULL, 
	tenant_id INTEGER, 
	invited_by INTEGER NOT NULL, 
	status VARCHAR(9) NOT NULL, 
	message TEXT, 
	expires_at DATETIME NOT NULL, 
	accepted_at DATETIME, 
	created_user_id INTEGER, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id), 
	FOREIGN KEY(invited_by) REFERENCES users (id), 
	FOREIGN KEY(created_user_id) REFERENCES users (id)
);
CREATE TABLE notifications (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	type VARCHAR(18) NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	message TEXT, 
	link VARCHAR(500), 
	is_read BOOLEAN NOT NULL, 
	read_at DATETIME, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);
CREATE TABLE password_resets (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	token_hash VARCHAR(255) NOT NULL, 
	expires_at DATETIME NOT NULL, 
	used_at DATETIME, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	UNIQUE (token_hash)
);
CREATE TABLE platforms (
	id INTEGER NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	slug VARCHAR(120) NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
);
CREATE TABLE rbac_policies (
	id INTEGER NOT NULL, 
	role VARCHAR(12) NOT NULL, 
	permissions TEXT NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	updated_by INTEGER, 
	published_at DATETIME, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(updated_by) REFERENCES users (id)
);
CREATE TABLE reading_progress (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	document_id INTEGER NOT NULL, 
	progress_percent INTEGER NOT NULL, 
	last_read_at DATETIME NOT NULL, 
	completed_at DATETIME, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(document_id) REFERENCES documents (id)
);
CREATE TABLE review_requests (
	id INTEGER NOT NULL, 
	document_id INTEGER NOT NULL, 
	version_id INTEGER, 
	submitted_by INTEGER NOT NULL, 
	reviewed_by INTEGER, 
	status VARCHAR(9) NOT NULL, 
	message TEXT, 
	review_comments TEXT, 
	submitted_at DATETIME NOT NULL, 
	reviewed_at DATETIME, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(document_id) REFERENCES documents (id), 
	FOREIGN KEY(version_id) REFERENCES versions (id), 
	FOREIGN KEY(submitted_by) REFERENCES users (id), 
	FOREIGN KEY(reviewed_by) REFERENCES users (id)
);
CREATE TABLE saved_searches (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	"query" VARCHAR(500), 
	category VARCHAR(100), 
	date_from DATETIME, 
	date_to DATETIME, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);
CREATE TABLE sections (
	id INTEGER NOT NULL, 
	version_id INTEGER NOT NULL, 
	"order" INTEGER NOT NULL, 
	title VARCHAR(500), 
	content TEXT, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(version_id) REFERENCES versions (id)
);
CREATE TABLE system_settings (
	id INTEGER NOT NULL, 
	"key" VARCHAR(100) NOT NULL, 
	value TEXT, 
	updated_by INTEGER, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(updated_by) REFERENCES users (id)
);
CREATE TABLE tenants (
	id INTEGER NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	slug VARCHAR(100) NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	settings TEXT, 
	company_logo VARCHAR(500), 
	contact_email VARCHAR(255), 
	company_type VARCHAR(50), 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
);
CREATE TABLE topics (
	id INTEGER NOT NULL, 
	name VARCHAR(150) NOT NULL, 
	slug VARCHAR(150) NOT NULL, 
	description TEXT, 
	image_url VARCHAR(500), 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
);
CREATE TABLE users (
	id INTEGER NOT NULL, 
	tenant_id INTEGER, 
	email VARCHAR(255) NOT NULL, 
	username VARCHAR(100) NOT NULL, 
	full_name VARCHAR(255) NOT NULL, 
	hashed_password VARCHAR(255) NOT NULL, 
	role VARCHAR(12) NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);
CREATE TABLE versions (
	id INTEGER NOT NULL, 
	document_id INTEGER NOT NULL, 
	version_number INTEGER NOT NULL, 
	semantic_version VARCHAR(32), 
	bump_type VARCHAR(5) NOT NULL, 
	content TEXT, 
	changes_summary TEXT, 
	is_published BOOLEAN NOT NULL, 
	published_at DATETIME, 
	published_by INTEGER, 
	created_by INTEGER NOT NULL, 
	row_version INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(document_id) REFERENCES documents (id), 
	FOREIGN KEY(published_by) REFERENCES users (id), 
	FOREIGN KEY(created_by) REFERENCES users (id)
);
CREATE UNIQUE INDEX ix_tenants_slug ON tenants (slug);
CREATE INDEX ix_tenants_id ON tenants (id);
CREATE UNIQUE INDEX ix_topics_slug ON topics (slug);
CREATE INDEX ix_topics_id ON topics (id);
CREATE UNIQUE INDEX ix_platforms_name ON platforms (name);
CREATE UNIQUE INDEX ix_platforms_slug ON platforms (slug);
CREATE INDEX ix_platforms_id ON platforms (id);
CREATE UNIQUE INDEX ix_domain_event_outbox_event_key ON domain_event_outbox (event_key);
CREATE INDEX ix_domain_event_outbox_created_at ON domain_event_outbox (created_at);
CREATE INDEX ix_domain_event_outbox_status ON domain_event_outbox (status);
CREATE INDEX ix_domain_event_outbox_next_attempt_at ON domain_event_outbox (next_attempt_at);
CREATE INDEX ix_domain_event_outbox_event_type ON domain_event_outbox (event_type);
CREATE INDEX ix_domain_event_outbox_id ON domain_event_outbox (id);
CREATE INDEX ix_idempotency_keys_user_id ON idempotency_keys (user_id);
CREATE INDEX ix_idempotency_keys_idempotency_key ON idempotency_keys (idempotency_key);
CREATE INDEX ix_idempotency_keys_status ON idempotency_keys (status);
CREATE INDEX ix_idempotency_keys_created_at ON idempotency_keys (created_at);
CREATE INDEX ix_idempotency_keys_id ON idempotency_keys (id);
CREATE INDEX ix_users_tenant_id ON users (tenant_id);
CREATE UNIQUE INDEX ix_users_email ON users (email);
CREATE INDEX ix_users_id ON users (id);
CREATE UNIQUE INDEX ix_users_username ON users (username);
CREATE UNIQUE INDEX ix_system_settings_key ON system_settings ("key");
CREATE INDEX ix_system_settings_id ON system_settings (id);
CREATE UNIQUE INDEX ix_rbac_policies_role ON rbac_policies (role);
CREATE INDEX ix_rbac_policies_id ON rbac_policies (id);
CREATE UNIQUE INDEX ix_documents_document_number ON documents (document_number);
CREATE INDEX ix_documents_platform ON documents (platform);
CREATE INDEX ix_documents_platform_id ON documents (platform_id);
CREATE INDEX ix_documents_parent_id ON documents (parent_id);
CREATE INDEX ix_documents_title ON documents (title);
CREATE INDEX ix_documents_topic ON documents (topic);
CREATE INDEX ix_documents_release_branch ON documents (release_branch);
CREATE INDEX ix_documents_category ON documents (category);
CREATE INDEX ix_documents_status ON documents (status);
CREATE INDEX ix_documents_tenant_id ON documents (tenant_id);
CREATE INDEX ix_documents_id ON documents (id);
CREATE INDEX ix_documents_visibility ON documents (visibility);
CREATE INDEX ix_notifications_user_id ON notifications (user_id);
CREATE INDEX ix_notifications_type ON notifications (type);
CREATE INDEX ix_notifications_id ON notifications (id);
CREATE INDEX ix_password_resets_id ON password_resets (id);
CREATE INDEX ix_password_resets_user_id ON password_resets (user_id);
CREATE INDEX ix_saved_searches_id ON saved_searches (id);
CREATE INDEX ix_saved_searches_user_id ON saved_searches (user_id);
CREATE INDEX ix_invitations_id ON invitations (id);
CREATE INDEX ix_invitations_status ON invitations (status);
CREATE INDEX ix_invitations_tenant_id ON invitations (tenant_id);
CREATE INDEX ix_invitations_email ON invitations (email);
CREATE UNIQUE INDEX ix_invitations_token ON invitations (token);
CREATE INDEX ix_versions_id ON versions (id);
CREATE INDEX ix_versions_semantic_version ON versions (semantic_version);
CREATE INDEX ix_versions_document_id ON versions (document_id);
CREATE INDEX ix_attachments_preview_pdf_storage_key ON attachments (preview_pdf_storage_key);
CREATE INDEX ix_attachments_sha256 ON attachments (sha256);
CREATE INDEX ix_attachments_document_id ON attachments (document_id);
CREATE INDEX ix_attachments_preview_pdf_sha256 ON attachments (preview_pdf_sha256);
CREATE INDEX ix_attachments_preview_pdf_status ON attachments (preview_pdf_status);
CREATE INDEX ix_attachments_storage_key ON attachments (storage_key);
CREATE INDEX ix_attachments_id ON attachments (id);
CREATE INDEX ix_attachments_reader_html_status ON attachments (reader_html_status);
CREATE INDEX ix_comments_parent_id ON comments (parent_id);
CREATE INDEX ix_comments_document_id ON comments (document_id);
CREATE INDEX ix_comments_id ON comments (id);
CREATE INDEX ix_audit_logs_created_at ON audit_logs (created_at);
CREATE INDEX ix_audit_logs_action ON audit_logs (action);
CREATE INDEX ix_audit_logs_document_id ON audit_logs (document_id);
CREATE INDEX ix_audit_logs_id ON audit_logs (id);
CREATE INDEX ix_audit_logs_user_id ON audit_logs (user_id);
CREATE INDEX ix_bookmarks_document_id ON bookmarks (document_id);
CREATE INDEX ix_bookmarks_user_id ON bookmarks (user_id);
CREATE INDEX ix_bookmarks_id ON bookmarks (id);
CREATE INDEX ix_feedbacks_user_id ON feedbacks (user_id);
CREATE INDEX ix_feedbacks_id ON feedbacks (id);
CREATE INDEX ix_feedbacks_status ON feedbacks (status);
CREATE INDEX ix_feedbacks_document_id ON feedbacks (document_id);
CREATE INDEX ix_reading_progress_document_id ON reading_progress (document_id);
CREATE INDEX ix_reading_progress_id ON reading_progress (id);
CREATE INDEX ix_reading_progress_user_id ON reading_progress (user_id);
CREATE INDEX ix_collaboration_sessions_session_id ON collaboration_sessions (session_id);
CREATE INDEX ix_collaboration_sessions_document_id ON collaboration_sessions (document_id);
CREATE INDEX ix_collaboration_sessions_id ON collaboration_sessions (id);
CREATE INDEX ix_collaboration_sessions_is_active ON collaboration_sessions (is_active);
CREATE INDEX ix_collaboration_sessions_user_id ON collaboration_sessions (user_id);
CREATE INDEX ix_collaboration_activities_user_id ON collaboration_activities (user_id);
CREATE INDEX ix_collaboration_activities_id ON collaboration_activities (id);
CREATE INDEX ix_collaboration_activities_session_id ON collaboration_activities (session_id);
CREATE INDEX ix_collaboration_activities_activity_type ON collaboration_activities (activity_type);
CREATE INDEX ix_collaboration_activities_created_at ON collaboration_activities (created_at);
CREATE INDEX ix_collaboration_activities_document_id ON collaboration_activities (document_id);
CREATE INDEX ix_collaboration_snapshots_created_at ON collaboration_snapshots (created_at);
CREATE INDEX ix_collaboration_snapshots_document_id ON collaboration_snapshots (document_id);
CREATE INDEX ix_collaboration_snapshots_snapshot_type ON collaboration_snapshots (snapshot_type);
CREATE INDEX ix_collaboration_snapshots_session_id ON collaboration_snapshots (session_id);
CREATE INDEX ix_collaboration_snapshots_id ON collaboration_snapshots (id);
CREATE INDEX ix_attachment_artifacts_id ON attachment_artifacts (id);
CREATE INDEX ix_attachment_artifacts_storage_key ON attachment_artifacts (storage_key);
CREATE INDEX ix_attachment_artifacts_kind ON attachment_artifacts (kind);
CREATE INDEX ix_attachment_artifacts_status ON attachment_artifacts (status);
CREATE INDEX ix_attachment_artifacts_sha256 ON attachment_artifacts (sha256);
CREATE INDEX ix_attachment_artifacts_attachment_id ON attachment_artifacts (attachment_id);
CREATE INDEX ix_attachment_conversion_jobs_status ON attachment_conversion_jobs (status);
CREATE INDEX ix_attachment_conversion_jobs_next_run_at ON attachment_conversion_jobs (next_run_at);
CREATE INDEX ix_attachment_conversion_jobs_id ON attachment_conversion_jobs (id);
CREATE INDEX ix_attachment_conversion_jobs_created_at ON attachment_conversion_jobs (created_at);
CREATE INDEX ix_attachment_conversion_jobs_job_type ON attachment_conversion_jobs (job_type);
CREATE INDEX ix_attachment_conversion_jobs_attachment_id ON attachment_conversion_jobs (attachment_id);
CREATE INDEX ix_sections_version_id ON sections (version_id);
CREATE INDEX ix_sections_id ON sections (id);
CREATE INDEX ix_review_requests_document_id ON review_requests (document_id);
CREATE INDEX ix_review_requests_status ON review_requests (status);
CREATE INDEX ix_review_requests_id ON review_requests (id);
COMMIT;
