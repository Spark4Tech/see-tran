**See Transit** 
A web app that brings together technical data from all public transit agencies in the US and worldwide.

**Data**
Transit agencies, industry vendors, and the technologies used to power public transportation.

**Key Entities**
Agencies, technology components, vendors, functional areas, functions, and integration.

**Access**
The landing page is publically available, as is the Agency list page; all other pages are auth protected.
Auth is provided via Microsoft or Google OAuth from application login page.
Registration is restricted to email addresses that are associated with an existing transit agency.

**Agencies**
Agencies have two user types: readers and admins; admins can update all Agency information (i.e. Agency Component relationships).
Agency data can be sourced via LLM or via community input (data source is indicated in app).

**Vendors**
Vendor registration is restricted to email addresses that are associated wtih an existing vendor.
Vendors have two user types: readers and admins; admins can update all Vendor information (i.e. Vendor Components Functional relationships).
Vendor data can be sourced via LLM or via community input (data source is indicated in app).
Vendors must have a paid subscription to use the hosted system (yearly subscription or included with sponsorship).

**Agents**
The application utilizes agents to find and update data in the hosted version (see-tran.org).
- Agency agent - gets agency information, vets it, creates or upscales
- Vendor agent - gets vendor information, vets it, creates or upscales
- Component agent - get component (and subcomponent) informration, vets it, creates or upscales

**Components**
Components are discrete products/solutions, provided by an internal IT team or third party vendor
that deliver technology in support of a discrete transit business function.
Components can be "nested" in order to handle sub components; a composite component is made up of
more than one nested sub-components.

**Roadmap:**
- Agency news
- Vendor news
- Transit technology news
- Forum
- SMS alerts

**See Transit is an open source project, created by industry enthusiasts.**
Contributions are welcomed from public transit teams.
See-Tran.org provides a hosted version with a growing set of community sourced up-to-date data, upscaled with AI.
