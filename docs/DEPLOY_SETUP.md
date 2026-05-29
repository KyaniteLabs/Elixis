# Tailscale OAuth Setup For CI/CD Deploy

**Status:** pending. The deploy job currently uses `continue-on-error: true` so build/test health stays visible while Tailscale OAuth credentials are configured.

## Why OAuth?

Tailscale OAuth clients are easier to scope and rotate than long-lived auth keys. Elixis deploys should use an ephemeral CI node tagged for deployment rather than a reused auth key.

## Prerequisites

- Tailscale admin access for the Kyanite Labs tailnet.
- GitHub repository admin access for `KyaniteLabs/Elixis`.

## 1. Create The CI Tag

In the Tailscale admin console, open **Access Controls** and define who may assign the CI tag. Replace the owner list with the real tailnet admin group or user.

```json
{
  "tagOwners": {
    "tag:ci": ["autogroup:admin"]
  }
}
```

Use the existing `tag:ci` definition if it already exists.

## 2. Create The OAuth Client

1. Open **Settings > OAuth Clients** in Tailscale.
2. Create a client named `GitHub Actions - Elixis Deploy`.
3. Grant the client the `auth_keys` scope.
4. Assign the client to `tag:ci`.
5. Copy the client ID and secret immediately; the secret is only shown once.

## 3. Add GitHub Secrets

Add these repository secrets under **Settings > Secrets and variables > Actions**:

| Secret | Value |
| --- | --- |
| `TS_OAUTH_CLIENT_ID` | Tailscale OAuth client ID |
| `TS_OAUTH_SECRET` | Tailscale OAuth client secret |

Remove any old `TAILSCALE_AUTHKEY` secret after OAuth deploys are confirmed.

## 4. Re-enable Strict Deploys

After the OAuth client works, remove `continue-on-error: true` from the deploy job in `.github/workflows/ci.yml`.

## Verification

1. Push a small change to `main`.
2. Confirm the deploy job completes successfully.
3. Confirm an ephemeral CI node appears in the Tailscale admin console during the run.
4. Confirm the `elixis` container on the VPS is running the expected image SHA.

## Troubleshooting

If Tailscale says the tag is invalid or not permitted, check that `tag:ci` exists, the OAuth client has the `auth_keys` scope, and the client is allowed to assign `tag:ci`.

If deploy reaches the VPS but the running image is wrong, inspect the `ELIXIS_IMAGE` line in `/docker/elixis/.env` and rerun the workflow after fixing the environment file.
