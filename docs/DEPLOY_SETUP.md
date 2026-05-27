# Tailscale OAuth Setup for CI/CD Deploy

**Status:** Pending — deploys use `continue-on-error: true` until credentials are configured.

## Why OAuth?

Tailscale auth keys are deprecated. OAuth clients provide a more secure, self-documenting authentication method. Once configured, no further credential rotation is needed.

---

## Prerequisites

- Tailscale admin access to your tailnet at [tailscale.com/admin](https://tailscale.com/admin)

---

## Step 1: Create a Tag for CI Nodes

Go to **Access Controls** in the Tailscale admin console and add a tag for CI runners:

```json
{
  "tages": {
    "tag:ci": []
  }
}
```

Or use the existing `tag:ci` tag if already defined.

---

## Step 2: Create an OAuth Client

1. Go to **Settings → OAuth Clients** in the Tailscale admin console
2. Click **Generate OAuth client**
3. Set a descriptive name (e.g., `GitHub Actions - Elixis Deploy`)
4. Select scopes:
   - `auth_keys` (required for registering ephemeral nodes)
5. Assign the tag `tag:ci`
6. Click **Generate client**
7. Copy the **Client ID** and **Client Secret** immediately — the secret is shown only once

---

## Step 3: Add GitHub Secrets

In the GitHub repository, go to **Settings → Secrets and variables → Actions** and add:

| Secret Name | Value |
|------------|-------|
| `TS_OAUTH_CLIENT_ID` | The OAuth client ID from Step 2 |
| `TS_OAUTH_SECRET` | The OAuth client secret from Step 2 |

> **Note:** `TAILSCALE_AUTHKEY` is no longer needed and can be removed.

---

## Step 4: Enable Deploy Job

Once the secrets are added, remove `continue-on-error: true` from the deploy job in `.github/workflows/ci.yml`:

```yaml
  deploy:
    needs: build
    runs-on: blacksmith-2vcpu-ubuntu-2404
    if: github.ref == 'refs/heads/main' || github.ref == 'refs/heads/master'
    environment: production
    # remove: continue-on-error: true
```

---

## Verification

After configuration:
1. Push a test commit to trigger the pipeline
2. Verify the deploy job completes successfully
3. Check Tailscale admin console — you should see ephemeral nodes appearing during deploys

---

## Troubleshooting

### "tags are invalid or not permitted"
- The OAuth client needs the `auth_keys` scope
- The tag `tag:ci` must be assigned to the OAuth client
- The tag must exist in your tailnet's access controls

### Auth key deprecation warning
Tailscale will eventually stop supporting auth keys entirely. OAuth is the recommended path.

---

## Cost & Maintenance

- **Cost:** Free for Tailscale users
- **Token expiry:** 1 hour (automatically renewed by GitHub Action)
- **Maintenance:** None after initial setup
