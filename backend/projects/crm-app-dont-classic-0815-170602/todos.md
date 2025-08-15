# Todo List

## Pending

- [⏳] Replace Home, Settings, Profile pages with CRM dashboard, settings (API keys modal), and user profile. Implement sidebar navigation and unified layout. [priority: high] (id: crm_frontend_pages)
- [⏳] Integrate frontend forms/pages with backend endpoints, including validation, error/loading states, and user data scoping. [priority: high] (id: crm_frontend_integration)
- [⏳] Implement API keys modal in Settings, with server-side storage and mock toggle. [integration: true] (id: crm_api_keys_modal)
- [⏳] Update README and add .env.example with demo instructions and run commands. [integration: true] (id: crm_readme_env)

## In Progress

- [🔄] Create comprehensive Python test file (`test_backend_comprehensive.py`) using requests and BACKEND_URL, covering all endpoints and flows. [priority: high] (id: crm_backend_tests)
- [🔄] Implement JWT authentication: registration, login, token issuance, and user context for all business endpoints. [priority: high] (id: crm_auth)
- [🔄] Implement user-scoped SQLAlchemy models (User, Contact, Company, Deal, Activity) and FastAPI endpoints for CRUD, with JWT auth protection. [priority: high] (id: crm_models_endpoints)

