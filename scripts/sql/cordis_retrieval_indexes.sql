-- Run outside a transaction. These expressions match CordisProjectRepository.
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cordis_projects_search
ON public.projects USING gin
(to_tsvector('english', COALESCE(title, '') || ' ' || COALESCE(objective, '') || ' ' || COALESCE(topics, '')));
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cordis_organizations_project
ON public.organizations ("projectID");
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cordis_organizations_pic
ON public.organizations ("organisationID");
