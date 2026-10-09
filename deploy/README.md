# Private two-container production stack

This folder contains a **tested deployment design**, not an assertion that any
internet-facing service is online. The private knowledge/data repository and
the reviewed server image must remain access restricted.

## Security boundary

- `Dockerfile.private-sealed`: builds a nonroot, **sealed** server containing
  only validated engine lookup tables, two reviewed runtime artifacts, and
  verified Python source. It does not include Canonical/Quarantine texts,
  the private manifest, source records, or the frontend.
- `Dockerfile.public-web`: builds the public React frontend from a separately
  prepared **frontend-only context**. It never sees the private knowledge
  repository and serves static files only.
- `nginx.conf`: proxies public API calls to an internal `tianji-api` service,
  denies public admin URLs and direct attempts to access data, runtime,
  configuration and schema paths.
- `compose.yml`: connects those two local images; **only the frontend** binds
  to host loopback. The API publishes no host port.

The private GitHub Action `Verify Private Sealed Release` builds both real
images in its **ephemeral private runner**, verifies SHA256, starts the actual
Compose stack, tests real Bazi and denies private paths. It **does not push
either image, persist a bundle, or deploy to a server**.

## Deploying when a private host or registry is available

1. Choose an owned host with Docker Compose, encrypted storage, access
   controls and HTTPS reverse proxy. Do not use a public image registry for
   the server image because its sealed artifacts contain confidential
   reviewed knowledge.
2. Transfer trusted images over a private channel, or publish the server image
   only to a verified restricted registry. Record **immutable image digests**
   and the independent `TIANJI_RUNTIME_SHA256` pin.
3. Set `TIANJI_PRIVATE_API_IMAGE` and `TIANJI_PUBLIC_WEB_IMAGE` to these
   locally available/private image tags. Set `TIANJI_HOST_PORT` to a loopback
   port if the default 8080 is occupied.
4. Run `docker compose -f deploy/compose.yml config --quiet`, then
   `docker compose -f deploy/compose.yml up -d` on that host. Test
   `http://127.0.0.1:8080/health` **locally**.
5. Terminate HTTPS at your managed reverse proxy and forward only to
   `127.0.0.1:8080`. Add rate limiting, logs without sensitive payloads,
   domain/TLS monitoring and a recovery plan **before** external publication.

No admin API is exposed through the public Nginx proxy. Establish a separate
authenticated management path before attempting admin operations.

The old public Git history remains accessible, notwithstanding the deletion of
knowledge files from public HEAD. Git history cleanup or migration to a
fresh clean-history public repository is a separate owner-approved operation.
