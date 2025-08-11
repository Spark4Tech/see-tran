TODO:

1. Fix Function display from Functional Areas - when a user clicks on a functional area, they should see the list of functions under that area in a clean and aligned manner
2. Fix Add Agency functionality - fix the error with adding an agency, only require required data, make sure all data can be included
3. Add Integrations page - agency users can create and maintain integrations at their agency, and can add new integration standards
4. Add Reports page - build initial Agency summary report; user can click a button can get a summary report with lots of good details in a web view, and can also click a button to download a CSV file
5. Add Auth - for Office365 Microsoft, and Google Workspace; only email addresses that match an agency or a vendor can log into the account using the OAuth function with Microsoft and Google. User model needs to capture the user type [agency, vendor (others types in the future)]
6. Add Edit controls - agency users should only be allowed to edit their own agency, based on the domain on their email account. vendor users should only be allowed to edit their own vendor record.
7. Create Add Agency agent (search data, build json, get logo and header)
- Configure agent to loop through a json agency list, with agency name and/or city
- See data/agency_template for data structure created by agent
- User can run agent manually, with a static json file of agencies

Goals: keep a consistent and clean user interface, easy to read, nicely styled with Tailwinds classes;
use HTMX when it makes sense, avoid excessive javascript; this app is designed to appeal to operational and technology employees who work in the transit industry, and vendors who serve that industry
