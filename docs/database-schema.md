# Database Schema

| Table | Columns (PK **bold**, FK in italics) | Notes |
|---|---|---|
| users | **id**, name, email (unique), password_hash, role, *manager_id* -> users, is_active, created_at | role CHECK in (admin, manager, employee); `manager_id` defines teams |
| projects | **id**, name (unique), description, is_archived, *created_by* -> users, created_at | |
| project_members | **project_id** -> projects, **user_id** -> users | composite PK, cascade delete |
| tasks | **id**, title, description, *project_id*, *assignee_id*, *manager_id*, priority, status, progress, start_date, deadline, completed_at, estimated_hours, actual_hours, review_feedback, rejection_count, reopen_count, last_progress_update, is_archived, *created_by*, created_at, updated_at | CHECK progress 0-100, priority and status enums; indexes on project_id, assignee_id, manager_id, status, deadline |
| task_history | **id**, *task_id*, *actor_id*, action, field, old_value, new_value, created_at | audit trail, one row per change |
| task_comments | **id**, *task_id*, *author_id*, body, created_at | progress notes also land here |
| code_analysis_reports | **id**, *submitted_by*, *task_id* (nullable), filename, language, line_count, code, syntax_valid, tools_used, notes, count_total/critical/high/medium/low/info, created_at | code limited to 50 KB by the API |
| code_analysis_findings | **id**, *report_id*, rule_id, severity, category, line, message, explanation, suggestion, tool | one report has many findings |
| prediction_records | **id**, *task_id*, risk_category, risk_score (nullable), method, model_version, factors (JSON), suggested_actions (JSON), created_at | `method` is `ml_model` or `rule_based` |
| token_blocklist | **id**, jti (unique), created_at | revoked tokens (logout) |

Tasks are archived, never hard-deleted, so history stays intact.
