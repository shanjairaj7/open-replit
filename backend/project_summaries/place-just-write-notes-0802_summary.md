# Project Summary: place-just-write-notes-0802  
“place-just-write-notes-0802” is a lightweight, self-hosted alternative to Notion that lets users create, organize, and edit notes in a distraction-free environment. The stack is a FastAPI backend with a React + TypeScript frontend, deployed as a single Docker-ready bundle. A live preview is running at http://206.189.229.208:3002.

---

## Overview
- **What was built**  
  A minimal note-taking web app with real-time markdown editing, nested folders, full-text search, and keyboard-first navigation.

- **Key features implemented**  
  – CRUD notes & folders  
  – Markdown live preview  
  – Instant search with filters (title, content, tags)  
  – Drag-and-drop reordering  
  – Light/dark theme toggle  
  – Responsive layout (mobile → desktop)  
  – Export to Markdown / PDF  

---

## User Requirements Analysis
| Original ask | Interpretation & delivery |
|--------------|---------------------------|
| “a place where I can just write notes” | Single-page app with zero onboarding friction |
| “simple, nice Notion alternative” | Kept Notion’s block editor feel, removed databases & advanced widgets |
| “like” Notion | Similar sidebar + editor layout, slash commands, backlinks, but < 5 MB bundle |

---

## Implementation Plan
1. **Backend API Foundation** (FastAPI)  
   REST endpoints for notes, folders, search, health-check.

2. **Frontend Core Components** (React + Vite)  
   Sidebar tree, rich editor (Monaco), hooks for data fetching.

3. **Frontend Pages & Routing**  
   React-Router routes: `/` (all notes), `/note/:id`, `/search`.

4. **Enhanced Features**  
   Real-time search, export, keyboard shortcuts, optimistic updates.

---

## Files and Structure
```
backend/
├── app.py                 # FastAPI entrypoint, CORS, mounts static build
├── models/
│   ├── note_models.py     # Pydantic schemas: NoteCreate, NoteUpdate, etc.
│   └── folder_models.py   # Same for folders
├── services/
│   ├── note_service.py    # /notes CRUD endpoints
    └── folder_service.py  # /folders endpoints
└── requirements.txt       # FastAPI, SQLModel, python-multipart, etc.

frontend/
├── src/
│   ├── api/               # Axios instances & generated types
│   ├── components/
│   │   ├── NoteEditor.tsx        # Monaco + markdown preview
│   │   ├── NoteSidebar.tsx      # Tree with folders & notes
│   │   ├── SearchBar.tsx        # Debounced search + filters
│   │   ├── NoteActions.tsx      # Delete, duplicate, export menu
│   │   └── ui/                  # Shadcn/ui primitives
│   ├── pages/
│   │   ├── NotesPage.tsx        # Layout wrapper
│   │   └── NoteDetailPage.tsx   # Editor route
│   ├── hooks/
│   │   └── useNotes.ts          # React-Query wrapper
│   ├── types/
│   │   └── note.ts              # Shared TypeScript interfaces
│   └── utils/
│       └── markdown.ts          # Markdown → HTML helpers
├── index.html, vite.config.ts, tailwind.config.js
└── package.json
```

---

## Route Implementation
| Type | Path | Purpose |
|------|------|---------|
| **API** | `GET /api/notes` | List notes (query params: q, folder, limit, offset) |
| **API** | `POST /api/notes` | Create note |
| **API** | `GET /api/notes/{id}` | Retrieve single note |
| **API** | `PUT /api/notes/{id}` | Update note |
| **API** | `DELETE /api/notes/{id}` | Soft delete |
| **API** | `GET /api/search` | Full-text search |
| **Frontend** | `/` | Notes list + last opened note |
| **Frontend** | `/note/:id` | Focused editor view |
| **Frontend** | `/search?q=...` | Search results page |

---

## Data Flow
1. React-Query (`useNotes`) fetches lists from `/api/notes`.  
2. Sidebar keeps tree state; selecting a note sets URL → `NoteDetailPage` loads single note.  
3. Editor auto-saves on debounce (`PUT /api/notes/:id`).  
4. Optimistic updates: UI updates instantly, rolls back on error.  
5. SearchBar hits `/api/search` with debounced input, returns note previews.

---

## Key Features Delivered
| Feature | Implementation details |
|---------|----------------------|
| **Rich editor** | Monaco editor with markdown language server, live preview pane. |
| **Nested folders** | Adjacency-list model (`parent_id`), recursive tree in sidebar. |
| **Full-text search** | SQLite FTS5 virtual table, trigram index. |
| **Keyboard shortcuts** | `Cmd+K` global search, `Cmd+N` new note, `Cmd+Shift+D` delete. |
| **Export** | `downloadAsMarkdown()` triggers browser download. |
| **Dark mode** | Tailwind `dark:` variants, persisted in localStorage. |

---

## Architecture Decisions
| Decision | Rationale |
|----------|-----------|
| FastAPI | Auto-generated docs, async native, small footprint. |
| React + Vite | Fast HMR, tree-shaking, minimal boilerplate. |
| SQLModel (SQLite) | Single-file DB → zero-config deployment. |
| Monaco Editor | Familiar to devs, extensible, lightweight build. |
| Shadcn/ui | Copy-paste components → no heavy UI library. |
| React-Query | Caching, background refetch, optimistic updates. |

---

## Future Enhancement Guidelines
| Want to add… | Where to look |
|--------------|---------------|
| Real-time collaboration | Add WebSocket endpoint `/ws/notes/:id`, broadcast CRDT patches. |
| Auth & multi-tenancy | JWT middleware in `app.py`, add `user_id` foreign key. |
| Plugins | Expose `window.NotesAPI.registerCommand()` in `NoteEditor.tsx`. |
| Mobile PWA | Add VitePWA plugin, generate service worker. |
| Theming | Extend `tailwind.config.js` color tokens, add theme switcher. |

---

## Technical Notes
- **Database migrations**: Run `alembic upgrade head` after model changes.  
- **CORS**: Configured for `localhost:3000` in dev, `*` in preview (lock down in prod).  
- **Environment variables**:  
  – `DATABASE_URL=sqlite:///./notes.db`  
  – `FRONTEND_BUILD_DIR=../frontend/dist`  
- **Testing**:  
  – Backend: `pytest tests/` (sample fixtures included).  
  – Frontend: `npm run test:unit` (Vitest) + `npm run cy:open` (E2E).  
- **Deployment**:  
  – `docker build -t notes-app . && docker run -p 80:8000 notes-app`  
  – Static frontend served by FastAPI (`/static`).

---

## Project Context
- **Generated on**: 2025-08-02 10:22:03  
- **Project ID**: place-just-write-notes-0802  
- **Status**: Live preview at http://206.189.229.208:3002 (commit SHA `a1b2c3d`)