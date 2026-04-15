BEGIN TRANSACTION;
CREATE TABLE activation_milestones (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	tenant_id INTEGER NOT NULL, 
	milestone VARCHAR(50) NOT NULL, 
	achieved_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_user_milestone UNIQUE (user_id, milestone)
);
CREATE TABLE admin_actions (
	id INTEGER NOT NULL, 
	action_type VARCHAR(22) NOT NULL, 
	status VARCHAR(9) NOT NULL, 
	payload TEXT NOT NULL, 
	reason TEXT, 
	requested_by INTEGER NOT NULL, 
	reviewed_by INTEGER, 
	review_comment TEXT, 
	target_tenant_id INTEGER, 
	created_at DATETIME NOT NULL, 
	reviewed_at DATETIME, 
	executed_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(requested_by) REFERENCES users (id), 
	FOREIGN KEY(reviewed_by) REFERENCES users (id), 
	FOREIGN KEY(target_tenant_id) REFERENCES tenants (id)
);
CREATE TABLE alembic_version (
	version_num VARCHAR(32) NOT NULL, 
	CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);
INSERT INTO "alembic_version" VALUES('20260328_0003');
CREATE TABLE announcements (
	id INTEGER NOT NULL, 
	message VARCHAR(500) NOT NULL, 
	type VARCHAR(20) NOT NULL, 
	active BOOLEAN NOT NULL, 
	created_by INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	expires_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(created_by) REFERENCES users (id)
);
CREATE TABLE api_keys (
	id INTEGER NOT NULL, 
	tenant_id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	key_prefix VARCHAR(8) NOT NULL, 
	key_hash VARCHAR(255) NOT NULL, 
	scopes TEXT, 
	is_active BOOLEAN NOT NULL, 
	last_used_at DATETIME, 
	expires_at DATETIME, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	UNIQUE (key_hash)
);
CREATE TABLE assistant_conversations (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	tenant_id INTEGER, 
	title VARCHAR(255) NOT NULL, 
	summary TEXT, 
	context_document_ids TEXT, 
	is_archived BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
);
CREATE TABLE assistant_messages (
	id INTEGER NOT NULL, 
	conversation_id INTEGER NOT NULL, 
	role VARCHAR(20) NOT NULL, 
	content TEXT, 
	tool_calls TEXT, 
	tool_call_id VARCHAR(100), 
	tool_name VARCHAR(100), 
	token_count INTEGER, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(conversation_id) REFERENCES assistant_conversations (id) ON DELETE CASCADE
);
CREATE TABLE assistant_uploaded_files (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	conversation_id INTEGER, 
	filename VARCHAR(255) NOT NULL, 
	original_filename VARCHAR(255) NOT NULL, 
	mime_type VARCHAR(100) NOT NULL, 
	file_size INTEGER NOT NULL, 
	storage_path VARCHAR(500) NOT NULL, 
	extracted_text TEXT, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(conversation_id) REFERENCES assistant_conversations (id) ON DELETE SET NULL
);
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
	FOREIGN KEY(document_id) REFERENCES documents (id) ON DELETE CASCADE, 
	FOREIGN KEY(uploaded_by) REFERENCES users (id)
);
CREATE TABLE audit_logs (
	id INTEGER NOT NULL, 
	user_id INTEGER, 
	document_id INTEGER, 
	action VARCHAR(8) NOT NULL, 
	audience_event_type VARCHAR(23), 
	details TEXT, 
	assignment_diff TEXT, 
	signature_key_id VARCHAR(32), 
	signature VARCHAR(128), 
	ip_address VARCHAR(45), 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
);
CREATE TABLE bookmarks (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	document_id INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(document_id) REFERENCES documents (id) ON DELETE CASCADE
);
CREATE TABLE broken_link_reports (
	id INTEGER NOT NULL, 
	document_id INTEGER NOT NULL, 
	version_id INTEGER NOT NULL, 
	broken_url VARCHAR(1000) NOT NULL, 
	link_text VARCHAR(500), 
	reason VARCHAR(200) NOT NULL, 
	scanned_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(document_id) REFERENCES documents (id) ON DELETE CASCADE, 
	FOREIGN KEY(version_id) REFERENCES versions (id) ON DELETE CASCADE
);
CREATE TABLE canned_responses (
	id INTEGER NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	content TEXT NOT NULL, 
	category VARCHAR(100), 
	created_by INTEGER NOT NULL, 
	tenant_id INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(created_by) REFERENCES users (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);
CREATE TABLE changelog_entries (
	id INTEGER NOT NULL, 
	title VARCHAR(300) NOT NULL, 
	content TEXT NOT NULL, 
	version_tag VARCHAR(50), 
	category VARCHAR(50), 
	published BOOLEAN NOT NULL, 
	created_by INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(created_by) REFERENCES users (id)
);
CREATE TABLE chat_messages (
	id INTEGER NOT NULL, 
	chat_id INTEGER NOT NULL, 
	sender_id INTEGER NOT NULL, 
	content TEXT NOT NULL, 
	message_type VARCHAR(6) NOT NULL, 
	context_json TEXT, 
	file_url VARCHAR(500), 
	file_name VARCHAR(255), 
	file_size INTEGER, 
	file_mime_type VARCHAR(100), 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	deleted_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(chat_id) REFERENCES chats (id) ON DELETE CASCADE
);
CREATE TABLE chat_participants (
	id INTEGER NOT NULL, 
	chat_id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	role VARCHAR(6) NOT NULL, 
	joined_at DATETIME NOT NULL, 
	last_read_at DATETIME, 
	is_muted BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_chat_participant UNIQUE (chat_id, user_id), 
	FOREIGN KEY(chat_id) REFERENCES chats (id) ON DELETE CASCADE
);
CREATE TABLE chats (
	id INTEGER NOT NULL, 
	type VARCHAR(6) NOT NULL, 
	name VARCHAR(255), 
	document_id INTEGER, 
	created_by INTEGER NOT NULL, 
	tenant_id INTEGER NOT NULL, 
	last_message_at DATETIME, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
);
CREATE TABLE collaboration_activities (
	id INTEGER NOT NULL, 
	document_id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	session_id VARCHAR(100), 
	activity_type VARCHAR(17) NOT NULL, 
	details TEXT, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
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
	PRIMARY KEY (id)
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
	PRIMARY KEY (id)
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
	FOREIGN KEY(document_id) REFERENCES documents (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(parent_id) REFERENCES comments (id)
);
CREATE TABLE data_requests (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	request_type VARCHAR(8) NOT NULL, 
	status VARCHAR(10) NOT NULL, 
	reason TEXT NOT NULL, 
	admin_comment TEXT, 
	reviewed_by INTEGER, 
	download_token VARCHAR(128), 
	download_expires_at DATETIME, 
	requested_at DATETIME NOT NULL, 
	approved_at DATETIME, 
	executed_at DATETIME, 
	completed_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(reviewed_by) REFERENCES users (id), 
	UNIQUE (download_token)
);
CREATE TABLE document_company_assignments (
	document_id INTEGER NOT NULL, 
	tenant_id INTEGER NOT NULL, 
	assigned_at DATETIME, 
	assigned_by INTEGER, 
	PRIMARY KEY (document_id, tenant_id), 
	FOREIGN KEY(document_id) REFERENCES documents (id) ON DELETE CASCADE, 
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
CREATE TABLE document_watchers (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	document_id INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_document_watchers_user_document UNIQUE (user_id, document_id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(document_id) REFERENCES documents (id) ON DELETE CASCADE
);
CREATE TABLE documents (
	id INTEGER NOT NULL, 
	tenant_id INTEGER NOT NULL, 
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
	due_date DATE, 
	thumbnail_url VARCHAR(500), 
	yjs_state BLOB, 
	created_by INTEGER NOT NULL, 
	deleted_by INTEGER, 
	deleted_at DATETIME, 
	purge_at DATETIME, 
	parent_id INTEGER, 
	row_version INTEGER NOT NULL, 
	audience_version INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id), 
	FOREIGN KEY(platform_id) REFERENCES platforms (id), 
	FOREIGN KEY(created_by) REFERENCES users (id), 
	FOREIGN KEY(deleted_by) REFERENCES users (id), 
	FOREIGN KEY(parent_id) REFERENCES documents (id) ON DELETE SET NULL
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
CREATE TABLE domain_verifications (
	id INTEGER NOT NULL, 
	tenant_id INTEGER NOT NULL, 
	domain VARCHAR(255) NOT NULL, 
	verification_token VARCHAR(128) NOT NULL, 
	status VARCHAR(8) NOT NULL, 
	verified_at DATETIME, 
	created_at DATETIME NOT NULL, 
	expires_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);
CREATE TABLE experiment_assignments (
	id INTEGER NOT NULL, 
	experiment_id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	variant VARCHAR(100) NOT NULL, 
	assigned_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_experiment_user UNIQUE (experiment_id, user_id), 
	FOREIGN KEY(experiment_id) REFERENCES experiments (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id)
);
CREATE TABLE experiment_metric_snapshots (
	id INTEGER NOT NULL, 
	experiment_id INTEGER NOT NULL, 
	variant VARCHAR(100) NOT NULL, 
	metric_name VARCHAR(100) NOT NULL, 
	metric_value VARCHAR(50) NOT NULL, 
	sample_size INTEGER NOT NULL, 
	recorded_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(experiment_id) REFERENCES experiments (id) ON DELETE CASCADE
);
CREATE TABLE experiments (
	id INTEGER NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	description TEXT, 
	feature_flag_key VARCHAR(100), 
	status VARCHAR(9) NOT NULL, 
	variants TEXT NOT NULL, 
	traffic_percentage INTEGER NOT NULL, 
	primary_metric VARCHAR(100), 
	guardrail_metrics TEXT, 
	guardrail_threshold INTEGER NOT NULL, 
	winner_variant VARCHAR(100), 
	tenant_id INTEGER, 
	created_by INTEGER NOT NULL, 
	started_at DATETIME, 
	ended_at DATETIME, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id), 
	FOREIGN KEY(created_by) REFERENCES users (id)
);
CREATE TABLE feature_flags (
	id INTEGER NOT NULL, 
	tenant_id INTEGER NOT NULL, 
	feature_key VARCHAR(100) NOT NULL, 
	enabled BOOLEAN NOT NULL, 
	rollout_percentage INTEGER, 
	target_tenant_ids TEXT, 
	updated_by INTEGER, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_tenant_feature UNIQUE (tenant_id, feature_key), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id), 
	FOREIGN KEY(updated_by) REFERENCES users (id)
);
CREATE TABLE feedbacks (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	document_id INTEGER NOT NULL, 
	feedback_type VARCHAR(10) NOT NULL, 
	status VARCHAR(9) NOT NULL, 
	content TEXT NOT NULL, 
	anchor_text TEXT, 
	response TEXT, 
	responded_by INTEGER, 
	responded_at DATETIME, 
	is_helpful BOOLEAN, 
	comment TEXT, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(document_id) REFERENCES documents (id) ON DELETE CASCADE, 
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
CREATE TABLE impersonation_sessions (
	id INTEGER NOT NULL, 
	admin_user_id INTEGER NOT NULL, 
	target_tenant_id INTEGER NOT NULL, 
	session_token VARCHAR(128) NOT NULL, 
	started_at DATETIME NOT NULL, 
	ended_at DATETIME, 
	is_active BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(admin_user_id) REFERENCES users (id), 
	FOREIGN KEY(target_tenant_id) REFERENCES tenants (id)
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
	email_delivery_status VARCHAR(10) NOT NULL, 
	email_delivery_attempt_count INTEGER NOT NULL, 
	email_last_attempted_at DATETIME, 
	email_last_sent_at DATETIME, 
	email_last_error TEXT, 
	email_last_subject VARCHAR(255), 
	email_last_sender_email VARCHAR(255), 
	email_last_sender_name VARCHAR(255), 
	created_user_id INTEGER, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id), 
	FOREIGN KEY(invited_by) REFERENCES users (id), 
	FOREIGN KEY(created_user_id) REFERENCES users (id)
);
CREATE TABLE maintenance_windows (
	id INTEGER NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	description TEXT, 
	scheduled_start DATETIME NOT NULL, 
	scheduled_end DATETIME NOT NULL, 
	is_read_only BOOLEAN NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	notification_sent BOOLEAN NOT NULL, 
	created_by INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(created_by) REFERENCES users (id)
);
CREATE TABLE notifications (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	type VARCHAR(23) NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	message TEXT, 
	link VARCHAR(500), 
	is_read BOOLEAN NOT NULL, 
	read_at DATETIME, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
);
CREATE TABLE nps_surveys (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	tenant_id INTEGER, 
	score INTEGER NOT NULL, 
	comment TEXT, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
);
CREATE TABLE onboarding_events (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	tenant_id INTEGER NOT NULL, 
	step VARCHAR(50) NOT NULL, 
	occurred_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
);
CREATE TABLE password_resets (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	token_hash VARCHAR(255) NOT NULL, 
	token_prefix VARCHAR(16), 
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
	FOREIGN KEY(document_id) REFERENCES documents (id) ON DELETE CASCADE
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
	reviewer_reminded_at DATETIME, 
	manager_escalated_at DATETIME, 
	created_at DATETIME NOT NULL, 
	audience_visibility_snapshot VARCHAR(50), 
	audience_company_ids_snapshot TEXT, 
	audience_version_snapshot INTEGER, 
	PRIMARY KEY (id), 
	FOREIGN KEY(document_id) REFERENCES documents (id) ON DELETE CASCADE, 
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
CREATE TABLE search_analytics (
	id INTEGER NOT NULL, 
	"query" VARCHAR(500) NOT NULL, 
	user_id INTEGER, 
	tenant_id INTEGER, 
	results_count INTEGER NOT NULL, 
	clicked_document_id INTEGER, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
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
CREATE TABLE security_events (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	event_type VARCHAR(64) NOT NULL, 
	ip_address VARCHAR(45), 
	user_agent VARCHAR(512), 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
);
CREATE TABLE support_ticket_assignments (
	id INTEGER NOT NULL, 
	ticket_id INTEGER NOT NULL, 
	agent_id INTEGER NOT NULL, 
	assigned_at DATETIME NOT NULL, 
	is_primary BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_ticket_assignment UNIQUE (ticket_id, agent_id), 
	FOREIGN KEY(ticket_id) REFERENCES support_tickets (id) ON DELETE CASCADE, 
	FOREIGN KEY(agent_id) REFERENCES users (id)
);
CREATE TABLE support_ticket_messages (
	id INTEGER NOT NULL, 
	ticket_id INTEGER NOT NULL, 
	sender_id INTEGER NOT NULL, 
	sender_type VARCHAR(20) NOT NULL, 
	content TEXT NOT NULL, 
	is_internal_note BOOLEAN NOT NULL, 
	file_name VARCHAR(255), 
	file_size INTEGER, 
	file_mime_type VARCHAR(100), 
	file_storage_key VARCHAR(500), 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(ticket_id) REFERENCES support_tickets (id) ON DELETE CASCADE, 
	FOREIGN KEY(sender_id) REFERENCES users (id)
);
CREATE TABLE support_tickets (
	id INTEGER NOT NULL, 
	customer_id INTEGER NOT NULL, 
	subject VARCHAR(500) NOT NULL, 
	status VARCHAR(11) NOT NULL, 
	priority VARCHAR(6) NOT NULL, 
	category VARCHAR(100), 
	feedback_id INTEGER, 
	tenant_id INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	resolved_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(customer_id) REFERENCES users (id), 
	FOREIGN KEY(feedback_id) REFERENCES feedbacks (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
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
CREATE TABLE tenant_quotas (
	id INTEGER NOT NULL, 
	tenant_id INTEGER NOT NULL, 
	max_users INTEGER, 
	max_documents INTEGER, 
	max_storage_mb INTEGER, 
	updated_by INTEGER, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_tenant_quota UNIQUE (tenant_id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id), 
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
CREATE TABLE user_sessions (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	session_token_hash VARCHAR(64) NOT NULL, 
	ip_address VARCHAR(45), 
	user_agent VARCHAR(512), 
	created_at DATETIME NOT NULL, 
	last_active_at DATETIME NOT NULL, 
	revoked_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
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
	is_email_verified BOOLEAN NOT NULL, 
	email_verification_token_hash VARCHAR(255), 
	email_verification_expires_at DATETIME, 
	failed_login_attempts INTEGER NOT NULL, 
	locked_until DATETIME, 
	last_login_ip VARCHAR(45), 
	last_login_user_agent VARCHAR(512), 
	timezone VARCHAR(64) NOT NULL, 
	locale VARCHAR(10) NOT NULL, 
	notification_preferences JSON, 
	onboarding_state JSON, 
	avatar_url VARCHAR(500), 
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
	scheduled_publish_at DATETIME, 
	scheduled_publish_audience_validated_at DATETIME, 
	audience_visibility_snapshot VARCHAR(50), 
	audience_company_ids_snapshot TEXT, 
	published_attachment_ids_snapshot TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(document_id) REFERENCES documents (id) ON DELETE CASCADE, 
	FOREIGN KEY(published_by) REFERENCES users (id), 
	FOREIGN KEY(created_by) REFERENCES users (id)
);
CREATE TABLE webhook_deliveries (
	id INTEGER NOT NULL, 
	webhook_id INTEGER NOT NULL, 
	event_type VARCHAR(120) NOT NULL, 
	payload_json TEXT NOT NULL, 
	response_status INTEGER, 
	response_body TEXT, 
	success BOOLEAN NOT NULL, 
	attempts INTEGER NOT NULL, 
	delivered_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(webhook_id) REFERENCES webhook_registrations (id) ON DELETE CASCADE
);
CREATE TABLE webhook_registrations (
	id INTEGER NOT NULL, 
	tenant_id INTEGER NOT NULL, 
	url VARCHAR(2048) NOT NULL, 
	secret VARCHAR(255) NOT NULL, 
	event_types TEXT NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	created_by INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id), 
	FOREIGN KEY(created_by) REFERENCES users (id)
);
CREATE INDEX ix_idempotency_keys_user_id ON idempotency_keys (user_id);
CREATE INDEX ix_idempotency_keys_id ON idempotency_keys (id);
CREATE INDEX ix_idempotency_keys_created_at ON idempotency_keys (created_at);
CREATE INDEX ix_idempotency_keys_idempotency_key ON idempotency_keys (idempotency_key);
CREATE INDEX ix_idempotency_keys_status ON idempotency_keys (status);
CREATE INDEX ix_tenants_id ON tenants (id);
CREATE UNIQUE INDEX ix_tenants_slug ON tenants (slug);
CREATE INDEX ix_topics_id ON topics (id);
CREATE UNIQUE INDEX ix_topics_slug ON topics (slug);
CREATE INDEX ix_platforms_id ON platforms (id);
CREATE UNIQUE INDEX ix_platforms_name ON platforms (name);
CREATE UNIQUE INDEX ix_platforms_slug ON platforms (slug);
CREATE INDEX ix_users_id ON users (id);
CREATE UNIQUE INDEX ix_users_username ON users (username);
CREATE UNIQUE INDEX ix_users_email ON users (email);
CREATE INDEX ix_users_tenant_id ON users (tenant_id);
CREATE INDEX ix_domain_verifications_tenant_id ON domain_verifications (tenant_id);
CREATE INDEX ix_domain_verifications_domain ON domain_verifications (domain);
CREATE INDEX ix_domain_verifications_id ON domain_verifications (id);
CREATE INDEX ix_domain_verifications_status ON domain_verifications (status);
CREATE INDEX ix_system_settings_id ON system_settings (id);
CREATE UNIQUE INDEX ix_system_settings_key ON system_settings ("key");
CREATE INDEX ix_rbac_policies_id ON rbac_policies (id);
CREATE UNIQUE INDEX ix_rbac_policies_role ON rbac_policies (role);
CREATE INDEX ix_documents_topic ON documents (topic);
CREATE INDEX ix_documents_id ON documents (id);
CREATE INDEX ix_documents_parent_id ON documents (parent_id);
CREATE INDEX ix_documents_status ON documents (status);
CREATE INDEX ix_documents_deleted_at ON documents (deleted_at);
CREATE INDEX ix_documents_release_branch ON documents (release_branch);
CREATE INDEX ix_documents_platform ON documents (platform);
CREATE INDEX ix_documents_visibility ON documents (visibility);
CREATE INDEX ix_documents_title ON documents (title);
CREATE INDEX ix_documents_tenant_id ON documents (tenant_id);
CREATE INDEX ix_documents_purge_at ON documents (purge_at);
CREATE INDEX ix_documents_platform_id ON documents (platform_id);
CREATE INDEX ix_documents_deleted_by ON documents (deleted_by);
CREATE UNIQUE INDEX ix_documents_document_number ON documents (document_number);
CREATE INDEX ix_documents_category ON documents (category);
CREATE INDEX ix_documents_due_date ON documents (due_date);
CREATE INDEX ix_changelog_entries_id ON changelog_entries (id);
CREATE INDEX ix_announcements_id ON announcements (id);
CREATE INDEX ix_user_sessions_created_at ON user_sessions (created_at);
CREATE INDEX ix_user_sessions_last_active_at ON user_sessions (last_active_at);
CREATE INDEX ix_user_sessions_id ON user_sessions (id);
CREATE UNIQUE INDEX ix_user_sessions_session_token_hash ON user_sessions (session_token_hash);
CREATE INDEX ix_user_sessions_revoked_at ON user_sessions (revoked_at);
CREATE INDEX ix_user_sessions_user_id ON user_sessions (user_id);
CREATE INDEX ix_password_resets_user_id ON password_resets (user_id);
CREATE INDEX ix_password_resets_id ON password_resets (id);
CREATE INDEX ix_password_resets_token_prefix ON password_resets (token_prefix);
CREATE INDEX ix_saved_searches_user_id ON saved_searches (user_id);
CREATE INDEX ix_saved_searches_id ON saved_searches (id);
CREATE UNIQUE INDEX ix_invitations_token ON invitations (token);
CREATE INDEX ix_invitations_email_delivery_status ON invitations (email_delivery_status);
CREATE INDEX ix_invitations_id ON invitations (id);
CREATE INDEX ix_invitations_tenant_id ON invitations (tenant_id);
CREATE INDEX ix_invitations_email ON invitations (email);
CREATE INDEX ix_invitations_status ON invitations (status);
CREATE INDEX ix_experiments_tenant_id ON experiments (tenant_id);
CREATE INDEX ix_experiments_id ON experiments (id);
CREATE INDEX ix_experiments_status ON experiments (status);
CREATE INDEX ix_experiments_feature_flag_key ON experiments (feature_flag_key);
CREATE INDEX ix_webhook_registrations_id ON webhook_registrations (id);
CREATE INDEX ix_webhook_registrations_tenant_id ON webhook_registrations (tenant_id);
CREATE INDEX ix_api_keys_tenant_id ON api_keys (tenant_id);
CREATE INDEX ix_api_keys_id ON api_keys (id);
CREATE INDEX ix_api_keys_user_id ON api_keys (user_id);
CREATE INDEX ix_impersonation_sessions_is_active ON impersonation_sessions (is_active);
CREATE INDEX ix_impersonation_sessions_id ON impersonation_sessions (id);
CREATE UNIQUE INDEX ix_impersonation_sessions_session_token ON impersonation_sessions (session_token);
CREATE INDEX ix_impersonation_sessions_admin_user_id ON impersonation_sessions (admin_user_id);
CREATE INDEX ix_impersonation_sessions_target_tenant_id ON impersonation_sessions (target_tenant_id);
CREATE INDEX ix_admin_actions_status ON admin_actions (status);
CREATE INDEX ix_admin_actions_id ON admin_actions (id);
CREATE INDEX ix_admin_actions_action_type ON admin_actions (action_type);
CREATE INDEX ix_admin_actions_requested_by ON admin_actions (requested_by);
CREATE INDEX ix_admin_actions_target_tenant_id ON admin_actions (target_tenant_id);
CREATE INDEX ix_tenant_quotas_tenant_id ON tenant_quotas (tenant_id);
CREATE INDEX ix_tenant_quotas_id ON tenant_quotas (id);
CREATE INDEX ix_feature_flags_id ON feature_flags (id);
CREATE INDEX ix_feature_flags_feature_key ON feature_flags (feature_key);
CREATE INDEX ix_feature_flags_tenant_id ON feature_flags (tenant_id);
CREATE INDEX ix_maintenance_windows_id ON maintenance_windows (id);
CREATE INDEX ix_maintenance_windows_scheduled_start ON maintenance_windows (scheduled_start);
CREATE INDEX ix_maintenance_windows_is_active ON maintenance_windows (is_active);
CREATE INDEX ix_data_requests_user_id ON data_requests (user_id);
CREATE INDEX ix_data_requests_id ON data_requests (id);
CREATE INDEX ix_data_requests_request_type ON data_requests (request_type);
CREATE INDEX ix_data_requests_status ON data_requests (status);
CREATE INDEX ix_canned_responses_id ON canned_responses (id);
CREATE INDEX ix_canned_responses_category ON canned_responses (category);
CREATE INDEX ix_canned_responses_tenant_id ON canned_responses (tenant_id);
CREATE INDEX ix_canned_responses_created_by ON canned_responses (created_by);
CREATE INDEX ix_document_company_assignments_document_id_tenant_id ON document_company_assignments (document_id, tenant_id);
CREATE INDEX ix_versions_id ON versions (id);
CREATE INDEX ix_versions_semantic_version ON versions (semantic_version);
CREATE INDEX ix_versions_document_id ON versions (document_id);
CREATE INDEX ix_versions_scheduled_publish_at ON versions (scheduled_publish_at);
CREATE INDEX ix_attachments_preview_pdf_status ON attachments (preview_pdf_status);
CREATE INDEX ix_attachments_sha256 ON attachments (sha256);
CREATE INDEX ix_attachments_preview_pdf_sha256 ON attachments (preview_pdf_sha256);
CREATE INDEX ix_attachments_document_id ON attachments (document_id);
CREATE INDEX ix_attachments_preview_pdf_storage_key ON attachments (preview_pdf_storage_key);
CREATE INDEX ix_attachments_storage_key ON attachments (storage_key);
CREATE INDEX ix_attachments_reader_html_status ON attachments (reader_html_status);
CREATE INDEX ix_attachments_id ON attachments (id);
CREATE INDEX ix_comments_document_id ON comments (document_id);
CREATE INDEX ix_comments_id ON comments (id);
CREATE INDEX ix_comments_parent_id ON comments (parent_id);
CREATE INDEX ix_bookmarks_document_id ON bookmarks (document_id);
CREATE INDEX ix_bookmarks_id ON bookmarks (id);
CREATE INDEX ix_bookmarks_user_id ON bookmarks (user_id);
CREATE INDEX ix_document_watchers_id ON document_watchers (id);
CREATE INDEX ix_document_watchers_user_id ON document_watchers (user_id);
CREATE INDEX ix_document_watchers_document_id ON document_watchers (document_id);
CREATE INDEX ix_feedbacks_user_id ON feedbacks (user_id);
CREATE INDEX ix_feedbacks_document_id ON feedbacks (document_id);
CREATE INDEX ix_feedbacks_status ON feedbacks (status);
CREATE INDEX ix_feedbacks_id ON feedbacks (id);
CREATE INDEX ix_reading_progress_document_id ON reading_progress (document_id);
CREATE INDEX ix_reading_progress_user_id ON reading_progress (user_id);
CREATE INDEX ix_reading_progress_id ON reading_progress (id);
CREATE INDEX ix_experiment_assignments_experiment_id ON experiment_assignments (experiment_id);
CREATE INDEX ix_experiment_assignments_user_id ON experiment_assignments (user_id);
CREATE INDEX ix_experiment_assignments_id ON experiment_assignments (id);
CREATE INDEX ix_experiment_metric_snapshots_experiment_id ON experiment_metric_snapshots (experiment_id);
CREATE INDEX ix_experiment_metric_snapshots_id ON experiment_metric_snapshots (id);
CREATE INDEX ix_experiment_metric_snapshots_recorded_at ON experiment_metric_snapshots (recorded_at);
CREATE INDEX ix_webhook_deliveries_id ON webhook_deliveries (id);
CREATE INDEX ix_webhook_deliveries_webhook_id ON webhook_deliveries (webhook_id);
CREATE INDEX ix_webhook_deliveries_delivered_at ON webhook_deliveries (delivered_at);
CREATE INDEX ix_attachment_artifacts_kind ON attachment_artifacts (kind);
CREATE INDEX ix_attachment_artifacts_attachment_id ON attachment_artifacts (attachment_id);
CREATE INDEX ix_attachment_artifacts_sha256 ON attachment_artifacts (sha256);
CREATE INDEX ix_attachment_artifacts_status ON attachment_artifacts (status);
CREATE INDEX ix_attachment_artifacts_storage_key ON attachment_artifacts (storage_key);
CREATE INDEX ix_attachment_artifacts_id ON attachment_artifacts (id);
CREATE INDEX ix_attachment_conversion_jobs_id ON attachment_conversion_jobs (id);
CREATE INDEX ix_attachment_conversion_jobs_created_at ON attachment_conversion_jobs (created_at);
CREATE INDEX ix_attachment_conversion_jobs_job_type ON attachment_conversion_jobs (job_type);
CREATE INDEX ix_attachment_conversion_jobs_next_run_at ON attachment_conversion_jobs (next_run_at);
CREATE INDEX ix_attachment_conversion_jobs_attachment_id ON attachment_conversion_jobs (attachment_id);
CREATE INDEX ix_attachment_conversion_jobs_status ON attachment_conversion_jobs (status);
CREATE INDEX ix_sections_version_id ON sections (version_id);
CREATE INDEX ix_sections_id ON sections (id);
CREATE INDEX ix_broken_link_reports_document_id ON broken_link_reports (document_id);
CREATE INDEX ix_broken_link_reports_id ON broken_link_reports (id);
CREATE INDEX ix_review_requests_id ON review_requests (id);
CREATE INDEX ix_review_requests_status ON review_requests (status);
CREATE INDEX ix_review_requests_document_id ON review_requests (document_id);
CREATE INDEX ix_support_tickets_status ON support_tickets (status);
CREATE INDEX ix_support_tickets_customer_id ON support_tickets (customer_id);
CREATE INDEX ix_support_tickets_priority ON support_tickets (priority);
CREATE INDEX ix_support_tickets_tenant_id ON support_tickets (tenant_id);
CREATE INDEX ix_support_tickets_category ON support_tickets (category);
CREATE INDEX ix_support_tickets_id ON support_tickets (id);
CREATE INDEX ix_support_tickets_feedback_id ON support_tickets (feedback_id);
CREATE INDEX ix_support_ticket_messages_created_at ON support_ticket_messages (created_at);
CREATE INDEX ix_support_ticket_messages_id ON support_ticket_messages (id);
CREATE INDEX ix_support_ticket_messages_sender_id ON support_ticket_messages (sender_id);
CREATE INDEX ix_support_ticket_messages_ticket_id ON support_ticket_messages (ticket_id);
CREATE INDEX ix_support_messages_ticket_created ON support_ticket_messages (ticket_id, created_at);
CREATE INDEX ix_support_ticket_messages_file_storage_key ON support_ticket_messages (file_storage_key);
CREATE INDEX ix_support_ticket_assignments_agent_id ON support_ticket_assignments (agent_id);
CREATE INDEX ix_support_ticket_assignments_id ON support_ticket_assignments (id);
CREATE INDEX ix_support_ticket_assignments_ticket_id ON support_ticket_assignments (ticket_id);
CREATE UNIQUE INDEX ix_domain_event_outbox_event_key ON domain_event_outbox (event_key);
CREATE INDEX ix_domain_event_outbox_id ON domain_event_outbox (id);
CREATE INDEX ix_domain_event_outbox_status ON domain_event_outbox (status);
CREATE INDEX ix_domain_event_outbox_event_type ON domain_event_outbox (event_type);
CREATE INDEX ix_domain_event_outbox_created_at ON domain_event_outbox (created_at);
CREATE INDEX ix_domain_event_outbox_next_attempt_at ON domain_event_outbox (next_attempt_at);
CREATE INDEX ix_audit_logs_document_id ON audit_logs (document_id);
CREATE INDEX ix_audit_logs_id ON audit_logs (id);
CREATE INDEX ix_audit_logs_action ON audit_logs (action);
CREATE INDEX ix_audit_logs_created_at ON audit_logs (created_at);
CREATE INDEX ix_audit_logs_user_id ON audit_logs (user_id);
CREATE INDEX ix_audit_logs_audience_event_type ON audit_logs (audience_event_type);
CREATE INDEX ix_security_events_id ON security_events (id);
CREATE INDEX ix_security_events_user_id ON security_events (user_id);
CREATE INDEX ix_security_events_event_type ON security_events (event_type);
CREATE INDEX ix_security_events_created_at ON security_events (created_at);
CREATE INDEX ix_search_analytics_tenant_id ON search_analytics (tenant_id);
CREATE INDEX ix_search_analytics_id ON search_analytics (id);
CREATE INDEX ix_search_analytics_user_id ON search_analytics (user_id);
CREATE INDEX ix_search_analytics_query ON search_analytics ("query");
CREATE INDEX ix_nps_surveys_id ON nps_surveys (id);
CREATE INDEX ix_nps_surveys_user_id ON nps_surveys (user_id);
CREATE INDEX ix_onboarding_user_step ON onboarding_events (user_id, step);
CREATE INDEX ix_onboarding_events_user_id ON onboarding_events (user_id);
CREATE INDEX ix_onboarding_events_tenant_id ON onboarding_events (tenant_id);
CREATE INDEX ix_onboarding_events_id ON onboarding_events (id);
CREATE INDEX ix_activation_milestones_id ON activation_milestones (id);
CREATE INDEX ix_activation_milestones_tenant_id ON activation_milestones (tenant_id);
CREATE INDEX ix_activation_milestones_user_id ON activation_milestones (user_id);
CREATE INDEX ix_assistant_conv_user_created ON assistant_conversations (user_id, created_at);
CREATE INDEX ix_assistant_conversations_id ON assistant_conversations (id);
CREATE INDEX ix_collaboration_sessions_is_active ON collaboration_sessions (is_active);
CREATE INDEX ix_collaboration_sessions_user_id ON collaboration_sessions (user_id);
CREATE INDEX ix_collaboration_sessions_id ON collaboration_sessions (id);
CREATE INDEX ix_collaboration_sessions_document_id ON collaboration_sessions (document_id);
CREATE INDEX ix_collaboration_sessions_session_id ON collaboration_sessions (session_id);
CREATE INDEX ix_collaboration_activities_document_id ON collaboration_activities (document_id);
CREATE INDEX ix_collaboration_activities_session_id ON collaboration_activities (session_id);
CREATE INDEX ix_collaboration_activities_created_at ON collaboration_activities (created_at);
CREATE INDEX ix_collaboration_activities_activity_type ON collaboration_activities (activity_type);
CREATE INDEX ix_collaboration_activities_user_id ON collaboration_activities (user_id);
CREATE INDEX ix_collaboration_activities_id ON collaboration_activities (id);
CREATE INDEX ix_collaboration_snapshots_session_id ON collaboration_snapshots (session_id);
CREATE INDEX ix_collaboration_snapshots_snapshot_type ON collaboration_snapshots (snapshot_type);
CREATE INDEX ix_collaboration_snapshots_id ON collaboration_snapshots (id);
CREATE INDEX ix_collaboration_snapshots_created_at ON collaboration_snapshots (created_at);
CREATE INDEX ix_collaboration_snapshots_document_id ON collaboration_snapshots (document_id);
CREATE INDEX ix_chats_last_message_at ON chats (last_message_at);
CREATE INDEX ix_chats_document_id ON chats (document_id);
CREATE INDEX ix_chats_id ON chats (id);
CREATE INDEX ix_chats_created_by ON chats (created_by);
CREATE INDEX ix_chats_tenant_id ON chats (tenant_id);
CREATE INDEX ix_notifications_type ON notifications (type);
CREATE INDEX ix_notifications_id ON notifications (id);
CREATE INDEX ix_notifications_user_id ON notifications (user_id);
CREATE INDEX ix_assistant_msg_conv_created ON assistant_messages (conversation_id, created_at);
CREATE INDEX ix_assistant_messages_id ON assistant_messages (id);
CREATE INDEX ix_assistant_file_user ON assistant_uploaded_files (user_id);
CREATE INDEX ix_assistant_uploaded_files_id ON assistant_uploaded_files (id);
CREATE INDEX ix_chat_participants_chat_id ON chat_participants (chat_id);
CREATE INDEX ix_chat_participants_user_id ON chat_participants (user_id);
CREATE INDEX ix_chat_participants_id ON chat_participants (id);
CREATE INDEX ix_chat_messages_chat_id ON chat_messages (chat_id);
CREATE INDEX ix_chat_messages_chat_created ON chat_messages (chat_id, created_at);
CREATE INDEX ix_chat_messages_id ON chat_messages (id);
CREATE INDEX ix_chat_messages_created_at ON chat_messages (created_at);
CREATE INDEX ix_chat_messages_sender_id ON chat_messages (sender_id);
COMMIT;
