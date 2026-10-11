# Human Operator Authentication

The review and alert APIs fail closed unless the request has a signed bearer token for a provisioned `EMERGENCY_COORDINATOR` or `ADMINISTRATOR` account. The former shared `admin/admin` mock login is removed.

## Configure and provision

Set `JWT_SECRET` in the local environment to a randomly generated secret of at least 32 characters. There is no built-in fallback key. If it is absent or too short, token issuance and validation return `503`.

Provision operator accounts interactively; the password is entered through a hidden prompt and stored as a salted PBKDF2-HMAC-SHA256 hash:

```powershell
python scripts/create_operator.py --username coordinator --email coordinator@example.gov.in --role EMERGENCY_COORDINATOR
```

Only the Emergency Coordinator and Administrator roles can access pending reviews, review decisions, and the alert history/dispatch routes. The authenticated token subject supplies the reviewer UUID and the token role supplies the role used by the approval policy. Request-body reviewer IDs and roles are ignored; they cannot be used to impersonate another operator.

The Human Review page provides sign-in and sign-out. Its bearer token is kept in session storage and attached by the API client. All alert records still use the explicitly simulated gateway; this authentication change does not enable live public dispatch.

## Verification

```powershell
pytest --basetemp .pytest-tmp apps/api/tests/test_operator_auth.py -q
Push-Location apps/web
npm run build
Pop-Location
```

The auth tests cover rejection of the old shared credentials, unauthenticated and non-operator denial, authenticated review/dispatch, reviewer identity binding, and password hash verification.
