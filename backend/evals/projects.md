* Todo App
  - Acceptable MVP:
    - add/edit/delete tasks (12)
    - mark complete (4)
    - list view (6)
    - responsive UI (9)
  - Full features:
    - categories/tags (7)
    - due dates & reminders (11)
    - search/filters (9)
    - completed history (6)
    - cloud sync/multi-device (14)
    - basic analytics (11)
  - Prompts:
    - Simple: "I need a simple todo app where I can jot down all the random stuff I need to do and check them off when I'm done. Nothing fancy, just clean and works on my phone."
    - Detailed: "I want something like Todoist but simpler. Need to organize tasks by projects and labels, set due dates with smart scheduling (like 'every Monday' or 'in 3 days'), natural language input like 'buy milk tomorrow #shopping @grocery', and those satisfying completion animations. Also want to see my productivity trends over time."
    - Technical: "Building a todo app with Notion-style databases, recurring task templates, AI-powered task suggestions based on patterns, calendar integration, collaborative task sharing, and analytics dashboard showing completion rates and time tracking like RescueTime."

* Landing Page
  - Acceptable MVP:
    - static responsive page with hero, features, pricing, CTA (14)
    - working contact form (7)
  - Full features:
    - SEO/OpenGraph (9)
    - testimonials (6)
    - A/B variants (11)
    - email integration (7)
    - analytics snippet (6)
    - fast load (5)
  - Prompts:
    - Simple: "I'm launching a SaaS product and need a professional landing page that doesn't look like I made it in 2010. Just something clean with a contact form so people can reach out."
    - Detailed: "Need a landing page like Stripe or Linear - that clean, modern look with smooth scrolling, animated hero section, interactive pricing calculator, social proof with logos, and A/B testing setup. Want that 'wow this looks expensive' vibe but still converts well."
    - Technical: "Building a high-converting landing page with Framer-style animations, dynamic pricing calculator like Notion's, testimonial carousel like Slack's, interactive product demos, conversion tracking, heatmap integration, and progressive web app features for mobile."


* Project Management App (Kanban-lite)
  - Acceptable MVP:
    - single-user app with projects + tasks [18] (18)
    - Kanban columns (To Do / Doing / Done) [14] (14)
    - create/edit tasks [11] (11)
    - basic dashboard [13] (13)
  - Full features:
    - multi-project boards [14] (14)
    - drag/drop Kanban [0] (18)
    - user accounts & roles [12] (22)
    - file attachments [0] (11)
    - calendar view [0] (13)
    - activity logs [0] (9)
    - notifications [0] (11)
    - charts [0] (16)
  - Prompts:
    - Simple: "I'm juggling too many projects and losing track of everything. Need something like Trello where I can see all my stuff in one place and move tasks around."
    - Detailed: "Want to build something like Monday.com but focused on our workflow. Need Kanban boards with custom statuses, time tracking like Toggl, Gantt charts for project timelines, automated status updates when tasks move, team workload view, and those satisfying progress bars. Also want Slack integration for notifications."
    - Technical: "Building an Asana/Linear hybrid with real-time collaboration, advanced filtering like Notion, custom field types, automation rules (when task moves to Done, create follow-up task), API for integrations, advanced permissions, and analytics dashboard showing team velocity and burndown charts."

* CRM App
  - Acceptable MVP:
    - single-user contacts CRUD (13)
    - simple pipeline (Lead → Contacted → Won/Lost) (16)
    - notes per contact (6)
    - search (7)
  - Full features:
    - RBAC/multi-user (25)
    - activity logs (calls/emails) (14)
    - import/export CSV (9)
    - calendar/email integrations (18)
    - audit trail (11)
    - advanced search/filters (11)
  - Prompts:
    - Simple: "I'm a freelancer and my client info is scattered across sticky notes and random text files. Need something to keep all their contact info, notes from calls, and track which ones are hot leads vs just inquiries."
    - Detailed: "Want a CRM like HubSpot but without the complexity. Need deal pipeline with drag-and-drop like Pipedrive, email tracking (know when they open proposals), automated follow-up reminders, contact scoring based on engagement, and revenue forecasting. Also want to import my Gmail contacts and see email history."
    - Technical: "Building a Salesforce-lite with custom fields, workflow automation (send email when deal reaches certain stage), integration with calendar/email providers, advanced reporting with conversion funnels, territory management, and AI-powered lead scoring based on interaction patterns."

* AI Document Management App
  - Acceptable MVP:
    - upload + view documents (PDF/DOCX/TXT) (14)
    - basic AI text summary per doc (22)
    - simple comments per document (7)
  - Full features:
    - collaborative editing (25)
    - highlights & inline comments (18)
    - version history & audit logs (14)
    - RBAC (18)
    - document-level search (14)
    - RAG-style citations (29)
    - LLM cost controls (11)
  - Prompts:
    - Simple: "I'm drowning in PDFs and Word docs for work. Just want to upload them somewhere and have AI tell me what's in each one so I don't have to read everything."
    - Detailed: "Want something like Notion AI but for document management. Upload contracts and get smart summaries, ask questions like 'what are the payment terms across all these contracts', highlight text with different colors like in Figma, real-time collaboration like Google Docs, and version history with visual diffs."
    - Technical: "Building a Dropbox + Notion + ChatGPT hybrid. Need OCR for scanned docs, semantic search across all documents, AI-powered document classification and tagging, collaborative editing with conflict resolution, advanced permissions like Google Workspace, and integration with DocuSign for contract workflows."

* Developer-Friendly Mixpanel Alternative (Analytics API + Dashboard)
  - Acceptable MVP:
    - event ingestion API endpoint (18)
    - dashboard showing event counts over time (14)
    - recent events table (single-tenant) (11)
  - Full features:
    - funnels (22)
    - cohorts/retention (25)
    - custom queries (18)
    - API keys (11)
    - CSV export (7)
    - scheduling/alerts (14)
    - multi-tenant/team support (22)
  - Prompts:
    - Simple: "Mixpanel is way too expensive for my startup. Need something simple where I can track what users are doing in my app and see basic charts about it."
    - Detailed: "Want to build PostHog but focused on our needs. Need event tracking with Amplitude-style user journeys, real-time dashboards like DataDog, A/B testing framework, cohort analysis for retention, and those slick animated charts like Linear's analytics. Also want Slack alerts when key metrics hit thresholds."
    - Technical: "Building a Mixpanel + Segment + LaunchDarkly combo. Need event streaming with real-time processing, advanced segmentation, predictive analytics for churn, feature flag management, custom dashboard builder like Grafana, and API for headless analytics integrations."

* Live Trading Prices App
  - Acceptable MVP:
    - search assets (9)
    - live price feed via public API (WebSocket or polling) (22)
    - simple dashboard displaying live quotes (13)
  - Full features:
    - portfolio/favorites persistence (11)
    - alerts/thresholds (18)
    - historical charts (16)
    - daily summary reports (email) (13)
  - Prompts:
    - Simple: "I'm always checking my phone for crypto prices. Want a clean dashboard where I can see live prices for Bitcoin, Ethereum, and a few stocks I'm watching."
    - Detailed: "Want something like Bloomberg Terminal but simpler and prettier. Need real-time crypto/stock prices with TradingView-style charts, portfolio tracking with P&L like Robinhood, price alerts via push notifications, news feed integration, and those satisfying animated numbers when prices change."
    - Technical: "Building a comprehensive trading platform with WebSocket data feeds, advanced charting like TradingView, algorithmic trading strategies, risk management tools, social trading features like eToro, backtesting engine, and integration with multiple exchanges via REST/WebSocket APIs."

* Multi-Doc RAG + Q&A App (decisive checkpoint)
  - Acceptable MVP:
    - multi-doc upload (18)
    - chunking + embeddings (29)
    - vector DB storage (25)
    - chat UI that answers with source citations/snippets (22)
    - deployed demo URL (14)
  - Full features:
    - robust chunking (22)
    - configurable retriever (k/filters) (18)
    - feedback loop for correctness (14)
    - paragraph-level citations (18)
  - Prompts:
    - Simple: "I have tons of research papers and docs for my thesis. Want to upload them all and chat with AI about them - like 'what does paper X say about topic Y' and get specific quotes."
    - Detailed: "Want to build something like Perplexity but for my own documents. Upload research papers, ask complex questions like 'compare these 5 papers on climate change models', get answers with inline citations, visual knowledge graphs showing connections between papers, and Claude-3-level reasoning about contradictions between sources."
    - Technical: "Building an advanced RAG system with multi-modal document processing, graph-based knowledge representation, agentic reasoning for complex queries, evaluation framework for citation accuracy, integration with academic databases, and collaborative research features like shared workspaces and annotation layers."

* Decisive checkpoint — When the model is "performing good" (single global test to flip the switch)
  - Which test to run: Test #8 — Multi-Doc RAG + Q&A
  - Pass criteria (all required):
    - Deployed MVP: reachable URL; upload → parse → chunk → embed → store works for mixed files (pdf/docx/txt); chat UI returns answers with visible citations (doc + snippet/paragraph) (36)
    - Three iterative improvements implemented: you issue 3 change requests; for each the model must deliver code diffs/PR or updated files, automated/manual test proving the change, and a redeployed demo. Example change requests: (a) paragraph-level citations, (b) latency/cost reduction via caching/batching, (c) RBAC + PII redaction on ingest (29)
    - Measurable improvements: model provides baseline metrics and post-change metrics. Minimal targets after iterations: citation precision ≥ 80%, median latency ≤ 2–3s (adjust to your SLA), plus documented cost-per-1k-queries (25)
    - Operational readiness: CI/CD / Docker deploy instructions; env var/secret handling; monitoring guidance; basic auth/rate limit/PII handling (22)
    - Reproducible tests: runnable QA scripts (sample docs + 20 benchmark queries + expected outputs or acceptance thresholds) and a README that reproduces the demo locally (18)
  - Decision rule: If Test #8 passes all pass criteria above, mark the model "performing good" — it is ready to reliably build, iterate, and deploy the other apps

---

## Point Summary

* Total Points: 1200

Project Breakdown:
- Todo App: 120 points (40 MVP + 80 Full)
- Landing Page: 90 points (30 MVP + 60 Full)
- Project Management App: 235 points (78 MVP + 157 Full)
- CRM App: 180 points (58 MVP + 122 Full)
- AI Document Management App: 240 points (60 MVP + 180 Full)
- Analytics Dashboard: 225 points (60 MVP + 165 Full)
- Live Trading App: 185 points (60 MVP + 125 Full)
- Multi-Doc RAG App: 350 points (150 MVP + 200 Full)
- Decisive Checkpoint: 180 points (Pass criteria)

Difficulty Distribution:
- Simple/Foundation: 210 points (Todo, Landing)
- Medium Complexity: 600 points (Project Mgmt, CRM, Trading, Analytics)
- Advanced/AI: 390 points (AI Docs, RAG, Checkpoint)


---

Test project IDs

- Project id: horizon-799-2237f
  project management app, signup and login, sidebar with organisations and tasks and dashboard with detailed overview of tasks and other buttons

- Project id: horizon-123-7101f
  Project Management App - Multi-user kanban with signup/login, organization management, task creation/assignment, kanban board (todo/in-progress), functional dashboard and sidebar. Team invitation functionality partially implemented (missing email integration). Good initial MVP with nice UI.
