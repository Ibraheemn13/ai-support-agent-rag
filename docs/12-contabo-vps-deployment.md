# Deploying SupportMind on a Contabo Ubuntu VPS

This deployment runs the complete product on one VPS with Docker Compose:

- Caddy on public ports 80/443 with automatic HTTPS
- Next.js frontend
- FastAPI API
- A separate RQ worker
- PostgreSQL 17 with pgvector
- Redis with append-only persistence
- Persistent Docker volumes for database data, uploads, queue data, and TLS

Only Caddy publishes host ports. PostgreSQL, Redis, the API, and the frontend
are reachable only on the private Compose network.

## Prerequisites

- Ubuntu 22.04, 24.04, or 26.04 on a 64-bit VPS
- At least 4 GB RAM; 8 GB is more comfortable while building the frontend
- A domain with two DNS names, such as `supportmind.example.com` and
  `api.supportmind.example.com`
- A GitHub repository URL and OpenAI API key
- SSH access to a non-root sudo user

## 0. Publish the Deployment Files

The VPS must clone a Git revision that includes the production Dockerfiles,
Compose stack, Caddy configuration, and this runbook. From the project folder
on your Windows computer, review and publish the current work:

```powershell
git status
git add .
git commit -m "Add Contabo VPS deployment"
git push origin main
```

If your deployment branch is not `main`, use that branch consistently in the
push and update commands below.

## 1. Point DNS at the VPS

At the domain provider, create two `A` records pointing to the Contabo public
IPv4 address:

```text
supportmind.example.com      -> YOUR_VPS_IPV4
api.supportmind.example.com  -> YOUR_VPS_IPV4
```

Remove an incorrect `AAAA` record unless IPv6 is configured on the VPS. Check
propagation from your computer:

```powershell
Resolve-DnsName supportmind.example.com
Resolve-DnsName api.supportmind.example.com
```

Do not start Caddy until both names resolve to the VPS. Public DNS plus open
ports 80 and 443 are required for certificate issuance.

## 2. Connect and Patch Ubuntu

```powershell
ssh YOUR_USER@YOUR_VPS_IP
```

Then on Ubuntu:

```bash
sudo apt update
sudo apt full-upgrade -y
sudo apt install -y ca-certificates curl git openssl ufw
sudo timedatectl set-timezone UTC
sudo reboot
```

Reconnect after the reboot.

## 3. Configure the Firewall

Allow SSH before enabling UFW:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status verbose
```

Also allow TCP 22, 80, and 443 in the Contabo control-panel firewall if one is
enabled. Do not open 3000, 5432, 6379, or 8000. Docker-published ports can
bypass UFW, which is why the Compose file publishes only Caddy's web ports.

## 4. Install Docker from the Official Repository

```bash
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io \
  docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
```

Log out and reconnect so the Docker group applies, then verify:

```bash
docker version
docker compose version
docker run --rm hello-world
```

Membership in the Docker group is effectively root access. Only grant it to
the deployment administrator.

## 5. Clone the Project

```bash
sudo mkdir -p /opt/supportmind
sudo chown "$USER:$USER" /opt/supportmind
git clone https://github.com/ZakwanZahid/ai-support-agent-rag.git \
  /opt/supportmind
cd /opt/supportmind
```

For a private repository, use a read-only GitHub deploy key instead of placing
a personal access token in shell history.

## 6. Create Production Secrets

Generate three URL-safe secrets:

```bash
openssl rand -hex 24  # POSTGRES_PASSWORD
openssl rand -hex 24  # APP_DB_PASSWORD; use a different value
openssl rand -hex 32  # JWT_SECRET_KEY
```

Create the untracked production environment file:

```bash
cp deploy/vps.env.example deploy/vps.env
nano deploy/vps.env
chmod 600 deploy/vps.env
```

Replace every placeholder. `APP_DOMAIN` and `API_DOMAIN` contain hostnames
only, without `https://` or trailing slashes. Keep the two database passwords
hex/alphanumeric because Compose embeds them in connection URLs.

Never commit `deploy/vps.env`. Confirm Git ignores it:

```bash
git check-ignore deploy/vps.env
```

## 7. Validate and Build

Every Compose command in this guide uses the same environment file:

```bash
docker compose --env-file deploy/vps.env -f compose.vps.yaml config --quiet
docker compose --env-file deploy/vps.env -f compose.vps.yaml build --pull
```

The frontend API URL is embedded during this build. Changing `API_DOMAIN`
later requires rebuilding the frontend image.

## 8. Start the Stack

```bash
docker compose --env-file deploy/vps.env -f compose.vps.yaml up -d
docker compose --env-file deploy/vps.env -f compose.vps.yaml ps
```

Startup order is enforced:

1. PostgreSQL and Redis become healthy.
2. The one-shot `migrate` container runs `alembic upgrade head`.
3. The API and worker start only after migrations succeed.
4. The frontend and Caddy start after the API becomes healthy.

The `migrate` service should show `Exited (0)`; that is success. Inspect logs:

```bash
docker compose --env-file deploy/vps.env -f compose.vps.yaml logs migrate
docker compose --env-file deploy/vps.env -f compose.vps.yaml logs --tail=100 api worker caddy
```

## 9. Verify the Deployment

```bash
curl -fsS "https://$(grep '^API_DOMAIN=' deploy/vps.env | cut -d= -f2)/health"
```

Then open:

```text
https://supportmind.example.com
https://api.supportmind.example.com/docs
```

Register a user, create a workspace and knowledge space, upload a small TXT or
PDF, prepare it, ask a question, and open the cited source.

Verify the database migration and private services:

```bash
docker compose --env-file deploy/vps.env -f compose.vps.yaml exec db \
  psql -U postgres -d supportmind -c "SELECT version_num FROM alembic_version;"

sudo ss -lntup
```

`ss` should show public listeners for SSH, 80, and 443, but not 3000, 5432,
6379, or 8000.

## 10. Configure Backups

The included backup script dumps PostgreSQL and archives uploaded originals:

```bash
chmod +x deploy/backup.sh
./deploy/backup.sh
ls -lh backups/
```

Schedule it daily as the deployment user:

```bash
crontab -e
```

Add:

```cron
15 3 * * * /opt/supportmind/deploy/backup.sh >> /opt/supportmind/backups/backup.log 2>&1
```

The default local retention is seven days. A backup on the same VPS does not
protect against VPS loss; sync the backup directory to encrypted off-site
object storage and periodically test restoration.

Redis is intentionally omitted because it stores transient queues and rate
limits, not authoritative product data.

Schedule stale-job recovery every five minutes in the same crontab:

```cron
*/5 * * * * cd /opt/supportmind && docker compose --env-file deploy/vps.env -f compose.vps.yaml exec -T api python sweep.py >> /opt/supportmind/backups/sweep.log 2>&1
```

## 11. Deploy Updates

```bash
cd /opt/supportmind
./deploy/backup.sh
git pull --ff-only
docker compose --env-file deploy/vps.env -f compose.vps.yaml build --pull
docker compose --env-file deploy/vps.env -f compose.vps.yaml up -d --remove-orphans
docker compose --env-file deploy/vps.env -f compose.vps.yaml ps
```

The migration image changes whenever backend code or migrations change, so
Compose reruns it before replacing dependent services.

## 12. Operations and Troubleshooting

Follow logs:

```bash
docker compose --env-file deploy/vps.env -f compose.vps.yaml logs -f api worker
```

Restart one service:

```bash
docker compose --env-file deploy/vps.env -f compose.vps.yaml restart worker
```

Run stale-work recovery:

```bash
docker compose --env-file deploy/vps.env -f compose.vps.yaml exec api python sweep.py
```

Check resource pressure:

```bash
docker stats
df -h
free -h
```

If HTTPS fails, verify DNS, ports 80/443, and `caddy` logs. If the API does not
start, inspect `migrate` first. If preparation remains queued, inspect `worker`
and `redis` health. If the frontend calls the wrong API hostname, rebuild it
after correcting `API_DOMAIN`.

## Security Follow-Up

- Confirm SSH-key login works before disabling password and root login.
- Enable unattended Ubuntu security updates.
- Enable Contabo account MFA and schedule VPS snapshots.
- Keep `.env`, database dumps, and OpenAI keys out of Git.
- Review logs and disk usage regularly.
- Upgrade base images and Python/Node dependencies routinely.
- Move uploads/backups to external object storage if this becomes more than a
  portfolio deployment.
