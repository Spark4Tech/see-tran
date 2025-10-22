See-Tran — Open source transit technology modeling and benchmarking
=================================================================

See-Tran is an open-source web application for modeling a transit agency’s technology landscape and benchmarking across agencies. It helps transit technology professionals catalog functional areas, map functions to components, track vendor products and versions, and understand integration points across the stack.

What you can do with See-Tran
- Model your current-state architecture: agencies → functional areas → functions → components
- Track real deployments using Configurations (agency + function + component)
- Map vendor Products and Product Versions used within each configuration
- Analyze vendor footprint and usage across agencies/functions
- View and share clean, print-friendly summaries for Functional Areas and Functions
- Browse internal documentation in-app (Markdown-based, at /docs)

Who it’s for
- Transit CIOs/CTOs and enterprise architects
- IT managers and application owners
- Vendor managers and procurement teams
- Analysts benchmarking capabilities and vendor presence across agencies

Core domain model (high level)
- Agency: A public transit organization using the platform
- FunctionalArea: A business domain (e.g., Operations, Maintenance, Planning)
- Function: A specific capability within a Functional Area; includes Criticality (high/medium/low)
- Component: A system or subsystem that implements one or more Functions
- Configuration: The key implementation record tying an Agency + Function + Component together, with status, deployment date, version label, and notes
- Vendor: A technology provider
- Product and ProductVersion: Vendor offerings and their releases; Products can be linked to Configurations via ConfigurationProduct
- IntegrationPoint and Standard: Where systems connect and which standards apply
- Tags and TagGroups: Lightweight classification for components/integrations

Key features (current)
- Functional Areas and Functions
	- Management UI with search and details
	- Print views:
		- /functional-areas/print — grid of all Functional Areas
		- /functions/print — all Functions grouped by Functional Area with criticality and quick counts
- Components
	- List with agency and function usage summaries (derived from Configurations)
	- Rich details pane including deployment recency, roles, and additional metadata
- Vendors and Products
	- Vendor list with product and usage counts (based on Product ↔ ConfigurationProduct links)
	- Vendor details grouped by Functional Area with used/unused products
	- Basic performance and usage metrics (most versions, most recent release, most used vendor)
- Agencies
	- List with synthetic implementation counts derived from Configurations
	- Basic stats: active implementations, average implementations per agency, average vendors per agency
- Configurations
	- The backbone of usage/benchmarking: each record represents a deployed component for a function at an agency
	- Supports associated products/versions through ConfigurationProduct
- Integrations and Standards
	- Integration points and referenced standards (basic list + relationships)
- Documentation (/docs)
	- Markdown-driven docs rendered in-app (fenced code, tables)
	- Responsive docs layout with sticky sidebar on desktop and a mobile drawer
- Accessibility and printing
	- Tailwind-based, responsive UI
	- Print-optimized pages for clean exports and sharing

Architecture and tech
- Backend: Flask (Python), SQLAlchemy ORM, Flask-Migrate (Alembic)
- Frontend: Jinja templates, Tailwind CSS, HTMX for dynamic fragments
- Auth: OAuth (Microsoft/Google) support in the hosted build
- Data: JSON bootstrap files and loader scripts in /data and /scripts
- Tests: Pytest stubs for health checks and core pages

Repository structure (selected)
- app/models/tran.py — Core data models (Agency, FunctionalArea, Function, Component, Vendor, Product, ProductVersion, Configuration, etc.)
- app/routes/ — Flask blueprints and HTML fragment endpoints
- app/templates/ — Jinja templates (pages and fragments)
- data/ — Seed JSON files for agencies, vendors, components, functions, etc.
- scripts/ — One-off data loader scripts
- tests/ — Basic tests and scaffolding

Getting started (local development)
1) Python environment
	 - Python 3.12+ recommended
	 - Create a virtual environment and install dependencies:
		 - python -m venv .venv
		 - source .venv/bin/activate
		 - pip install -r requirements.txt
	 - Note: Markdown is required for /docs (tracked in requirements.txt)

2) Run the app
	 - export FLASK_APP=run.py
	 - flask run
	 - Visit http://localhost:5000

3) Optional: load seed data
	 - Review /scripts and /data for example loaders
	 - Ensure database migrations are initialized (Flask-Migrate/Alembic)

Modeling and benchmarking tips
- Use Functional Areas and Functions to define business capabilities and their criticality
- Use Components to represent systems; relate them to Functions
- Create Configurations for each real deployment at an Agency; include dates and status
- Link Products and Product Versions to Configurations via ConfigurationProduct to track vendor footprint
- Use the Vendors pages to see product counts and active usage across agencies/functions
- Use the print pages to circulate summaries in meetings or attach to reports

Security and access
- Public pages: landing and agency list (config-dependent)
- Auth-protected pages for management and benchmarking screens
- OAuth (Microsoft/Google) supported for hosted builds; registration limited to known agency/vendor domains
- Super admin role (config) with full access; agency/vendor-level roles planned/available per route configuration

Roadmap (abridged)
- Deeper benchmarking dashboards (cross-agency comparisons, trends)
- Enhanced integration mapping and standards coverage
- Vendor/agency news feeds and alerts
- Collaboration features for community curation

Contributing
We welcome contributions from public transit teams and industry partners. Please open issues for bugs and feature requests, and submit pull requests for proposed changes. See the project docs (/docs) for domain notes and contribution guidelines as they evolve.

Hosted option
See-Tran.org provides a hosted instance with community-sourced data enhanced by AI agents for discovery and normalization. Contact the maintainers if you’d like to participate or pilot.
