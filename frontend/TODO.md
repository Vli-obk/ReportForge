# TODO - PDF Analytics SaaS Platform

## Phase 1: Route wiring + critical UI fixes
- [ ] Verify/ensure Next.js routes exist for:
  - [ ] /home/dashboard
  - [ ] /home/uploads
  - [ ] /home/datasets
  - [ ] /home/analytics
  - [ ] /home/pipeline
  - [ ] /home/settings
- [x] Fix bug in `UploadsPage` where data fetch uses `useState` instead of `useEffect`.
- [ ] (prettier follow-up) Format new route wrapper pages and updated pages to satisfy lint.

- [ ] Replace mock charts in `AnalyticsPage` with API-driven data.

## Phase 2: Pipeline + dashboard integration
- [ ] Implement dataset explorer filters + column inspector UX.
- [ ] Improve pipeline monitoring with logs/pipeline stages.

## Phase 3: Settings + DevOps
- [ ] Implement Settings page using real API/config endpoints.
- [ ] Dockerize frontend + backend and add docker-compose with Postgres.

