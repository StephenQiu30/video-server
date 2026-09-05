"""Current retained bytes and reservations, including pending physical deletion."""

from sqlalchemy import text

# Import jobs already have a download projection and must be counted only once.
# Workers replace active reservations with bounded artifacts in one transaction.
ACTIVE_USAGE = text("""
WITH active AS (
    SELECT j.owner_hash, COALESCE(q.reserved_bytes,
        m.declared_size_bytes + :thumbnail_bytes,
        :download_bytes + :thumbnail_bytes) AS reserved_bytes
    FROM download_jobs j
    LEFT JOIN resource_admissions q ON q.id = j.id
    LEFT JOIN media_imports m ON m.id = j.id
    WHERE j.status IN ('queued', 'running', 'retry_wait')
    UNION ALL
    SELECT d.owner_hash, COALESCE(q.reserved_bytes,
        d.declared_size_bytes + :document_bytes)
    FROM documents d LEFT JOIN resource_admissions q ON q.id = d.id
    WHERE d.status IN ('uploading', 'verifying')
    UNION ALL
    SELECT j.owner_hash, COALESCE(q.reserved_bytes, :report_bytes)
    FROM analysis_jobs j
    LEFT JOIN resource_admissions q ON q.id = j.active_run_id
    WHERE j.status IN ('queued', 'running', 'retry_wait')
    UNION ALL
    SELECT j.owner_hash, COALESCE(q.reserved_bytes, :report_bytes)
    FROM analysis_report_versions r
    JOIN analysis_jobs j ON j.id = r.job_id
    LEFT JOIN resource_admissions q ON q.id = r.run_id
    WHERE r.status IN ('publishing', 'publish_failed', 'delete_pending')
      AND (j.status NOT IN ('queued', 'running', 'retry_wait')
           OR j.active_run_id <> r.run_id)
      AND NOT EXISTS (SELECT 1 FROM analysis_report_artifacts a
                      WHERE a.report_id = r.id)
)
SELECT COUNT(*) AS global_active,
    COUNT(*) FILTER (WHERE owner_hash = :owner) AS owner_active,
    COALESCE(SUM(reserved_bytes) FILTER (WHERE owner_hash = :owner), 0) AS reserved
FROM active
""")

# Download tombstones precede object deletion. Documents and all report versions
# remain charged until their physical cleanup records reach the deleted state.
STORED_BYTES = text("""
SELECT COALESCE(SUM(size_bytes), 0) FROM (
    SELECT a.size_bytes FROM artifacts a
    JOIN download_jobs j ON j.id = a.job_id WHERE j.owner_hash = :owner
    UNION ALL
    SELECT t.size_bytes FROM download_thumbnails t
    JOIN download_jobs j ON j.id = t.job_id WHERE j.owner_hash = :owner
    UNION ALL
    SELECT a.size_bytes FROM document_artifacts a
    JOIN documents d ON d.id = a.document_id
    WHERE d.owner_hash = :owner AND a.status <> 'deleted'
    UNION ALL
    SELECT a.size_bytes FROM analysis_report_artifacts a
    JOIN analysis_report_versions r ON r.id = a.report_id
    JOIN analysis_jobs j ON j.id = r.job_id
    WHERE j.owner_hash = :owner AND a.status <> 'deleted'
) stored
""")
