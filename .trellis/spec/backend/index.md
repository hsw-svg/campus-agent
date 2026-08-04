# Backend Development Guidelines

> Best practices for backend development in this project.

---

## Overview

This directory contains guidelines for backend development. Fill in each file with your project's specific conventions.

---

## Guidelines Index

| Guide | Description | Status |
|-------|-------------|--------|
| [Directory Structure](./directory-structure.md) | Module organization and file layout | To fill |
| [Database Guidelines](./database-guidelines.md) | ORM patterns, queries, migrations | To fill |
| [Error Handling](./error-handling.md) | Error types, handling strategies | To fill |
| [Quality Guidelines](./quality-guidelines.md) | Code standards, forbidden patterns | To fill |
| [Logging Guidelines](./logging-guidelines.md) | Structured logging, log levels | To fill |
| [Attachment Upload](./attachment-upload.md) | Course/workspace upload API, validation, isolation, and frontend concurrency contract | Active |
| [Agent Intent Routing](./agent-intent-routing.md) | Semantic candidate retrieval, Intent LLM selection, and non-blocking fallback contract | Active |
| [Teacher Standalone Agents](./teacher-standalone-agents.md) | Trusted no-course workflow guard, empty-material exceptions, and metadata compatibility | Active |
| [Campus News](./campus-news.md) | Official-source ingestion, persistent cache, degradation API, and student-home presentation contract | Active |
| [Student Course Center](./student-course-center.md) | Default course catalog, chapters, progress, evidence-backed weak points, and student learning context | Active |
| [Student Resume Assistant](./student-resume-assistant.md) | Current resume selection, course evidence snapshots, structured analysis Artifacts, and history isolation | Active |
| [Slide Deck Templates](./slide-deck-templates.md) | Controlled LLM template selection, source-slide cloning, manifest-driven text filling, and PPTX export compatibility | Active |
| [DeepTutor Integration](./deeptutor-integration.md) | Same-origin DeepTutor book/page/knowledge-base adapter, WebSocket proxy, and single-container runtime contract | Active |

---

## How to Fill These Guidelines

For each guideline file:

1. Document your project's **actual conventions** (not ideals)
2. Include **code examples** from your codebase
3. List **forbidden patterns** and why
4. Add **common mistakes** your team has made

The goal is to help AI assistants and new team members understand how YOUR project works.

---

**Language**: All documentation should be written in **English**.
