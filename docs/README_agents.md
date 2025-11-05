# See‑Tran: Agent‑assisted crowdsourcing guide

See‑Tran is an open‑source web app for modeling a transit agency’s technology landscape and benchmarking across agencies. This guide explains how the app is organized today, how people at public transit agencies can contribute high‑quality data, and where “agents” (automated helpers) fit in to scale coverage across the U.S., Canada, and Mexico.

## What the app does

- Catalogs the architecture of transit technology: agencies → functional areas → functions → components
- Tracks real deployments using Configurations (Agency + Function + Component)
- Links vendor Products and Product Versions used within those configurations
- Provides fast, printable summaries and lightweight analytics to compare vendors and capabilities
- Uses a simple, responsive UI with HTMX for quick, fragment‑level updates (no page reload)

## Core data model (mental map)

- Agency: A public transit organization
- FunctionalArea: Business domains (e.g., Operations, Planning, Maintenance)
- Function: A capability within a Functional Area; has Criticality (high/medium/low)
- Component: A system/subsystem that implements one or more Functions
- Configuration: The implementation record – ties an Agency + Function + Component together, with Status, Deployment Date, Version Label, and Notes
- Vendor: Technology provider
- Product, ProductVersion: Vendor offerings and releases; linked to Configurations via ConfigurationProduct
- IntegrationPoint, Standard: Where systems connect and which standards apply (early stage)
- Tags/TagGroups: Lightweight classification (optional)

Uniqueness highlights and assumptions:
- Agency.name and Vendor.name are unique
- Product.name is unique; ProductVersion is unique on (product_id, version)
- Configuration is unique per (agency_id, function_id, component_id)
- A Component is a system used by agencies; a Product is a vendor’s offering linked to usage via ConfigurationProduct

## How contributors use the app

1) Browse and search
- Functional Areas and Functions have dedicated pages, including print‑friendly views
- Components and Vendors show quick usage stats derived from Configurations

2) Create a Configuration (the backbone)
- From the Configurations page:
  - Filters: Agency, Function, Status (with live function search)
  - Quick Create: pick Functional Area → search/select Function → pick Component → select Status → Create
  - Wizard: guided steps; when you come from an agency page, the agency is preselected
- After creating a Configuration, optionally attach Products/Versions in the details panel

3) Keep entities tidy
- Keep Function names concise, use criticality to indicate importance
- Components represent systems; don’t duplicate by environment (use Status/Notes/Version Label)
- Products/Versions reflect vendor nomenclature

4) Print and share
- /functional‑areas/print and /functions/print offer clean summaries for meetings and reports

## Where agents fit (today and near‑term)

Located in `app/agents/` (scaffolded, evolving):
- agency_agent.py: discovers/updates agency facts (description, contacts, web assets, logos, headers)
- vendor_agent.py: builds/updates vendor profiles (news, products, metadata)
- component_agent.py: maps components, functions supported, and relationships

Initial operating model (human‑in‑the‑loop):
- “Suggest” mode: agents propose additions/edits with provenance (URLs, timestamps)
- Reviewer UI (planned): human curators accept/modify/reject suggestions
- Batch seeding: agents help bootstrap Agencies, Vendors, Components, and candidate Functions per agency

Data quality principles for agents:
- Verifiable sources only; include links
- Prefer official sites over third‑party directories
- Don’t guess: mark uncertain fields and route to reviewers
- Normalize names (e.g., remove marketing fluff; consistent casing)

## App architecture (in brief)

- Backend: Flask + SQLAlchemy + Alembic (migrations)
- Frontend: Jinja templates, Tailwind CSS, HTMX fragments
- Auth: login_required applied to authoring endpoints; OAuth for hosted builds
- Data: seed JSON and loader scripts in `/data` and `/scripts`
- Tests: basic pytest coverage; expand as features stabilize

Key folders you’ll use:
- `app/models/tran.py` – All core models (Agency, FunctionalArea, Function, Component, Vendor, Product, ProductVersion, Configuration…)
- `app/routes/` – Blueprints and fragment endpoints (e.g., configurations, vendors, products)
- `app/templates/` – Pages and fragment templates (HTMX targets)
- `docs/` – Project docs (this file, setup, roadmap)
- `data/` – Example seed data; agency/vendor/product/component JSON
- `scripts/` – Data loaders and utilities

HTMX patterns (how the UI stays fast):
- Lists load into fragments (`#…-list`) on `hx-trigger="load"`
- Filters and searches return lightweight HTML partials (e.g., `<option>` lists)
- Forms post to API routes that return one row or a refreshed fragment

## Roles and moderation (crowdsourcing posture)

- Authenticated contributors (agency staff, partners) can propose data
- Moderators (trusted curators) review suggestions and resolve conflicts
- Agency‑scoped permissions for sensitive edits are planned for hosted deployments

## Privacy and scope

- Keep personal data out; use organizational contacts where possible
- Public facts only (websites, official docs, procurements)
- The goal is comprehensive, verifiable coverage across US, Canada, and Mexico

## Roadmap for agents and curation

- Deep research agents for agencies and vendors with deduplication
- Product–Function alignment at scale; heuristic + reviewer confirmation
- Integration mapping and standards coverage
- Enhanced search (full‑text) and similarity (peer agency recommendations)
- Reviewer dashboards and bulk actions

## Quick start (local)

- Python 3.12+, `pip install -r requirements.txt`
- `flask run` or `python run.py`
- Optional: load sample data from `/data` via scripts in `/scripts`

Have feedback or want to help? Open an issue or PR, or reach out to the maintainers. Our aim is to make it easy for transit professionals to document and compare their technology — with transparent, trustworthy data and helpful automation.
