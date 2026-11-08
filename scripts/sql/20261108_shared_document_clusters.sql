-- Repair legacy WP part numbers incorrectly stored as Horizon cluster numbers.
-- Do not infer a revision date or override the period printed in historical PDFs.
BEGIN;
UPDATE shared_documents
SET scope = 'cluster',
    scope_identifier = 'CLUSTER-' ||
        ((substring(document_url from '/wp-([4-9])-'))::integer - 3)::text
WHERE document_type = 'work_programme'
  AND document_url ~ '/wp-[4-9]-';

UPDATE shared_documents
SET document_title = 'Horizon Europe Work Programme 2023–2025 — 4. Health'
WHERE document_url LIKE '%/2023-2024/wp-4-health_%'
  AND document_title LIKE '%General Introduction%'
  AND document_content LIKE '%Health%';
COMMIT;
