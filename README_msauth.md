To set up in MS AD/Entra to allow login
https://login.microsoftonline.com/common/v2.0/adminconsent
  ?client_id=<YOUR_CLIENT_ID>
  &redirect_uri=https://<your-domain>/auth/microsoft/callback
  &state=<opaque_state>