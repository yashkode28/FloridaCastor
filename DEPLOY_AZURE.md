# Deploying FloridaCastor to Azure Container Apps

Flask + Gunicorn → Azure Container Apps + Azure Database for PostgreSQL.

---

## Pre-flight checklist

Before starting, make sure you have:

- [ ] [Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli) installed (`brew install azure-cli` on Mac)
- [ ] Logged in: `az login`
- [ ] Container Apps extension: `az extension add --name containerapp --upgrade`
- [ ] Docker Desktop running

---

## Step 0 — Set your variable names

Paste these into your terminal. Every command below uses them.
Replace the values in `< >` with your own choices.

```bash
RESOURCE_GROUP=floridacastor-rg
LOCATION=eastus                          # or eastus2, westus2, etc.
ACR_NAME=floridacastoracr                # globally unique, lowercase letters and numbers only
ENVIRONMENT=floridacastor-env
APP_NAME=floridacastor
POSTGRES_SERVER=floridacastor-db         # globally unique
DB_ADMIN_USER=weatheradmin
DB_ADMIN_PASSWORD="<YOUR_STRONG_PASSWORD>"  # needs: uppercase + number + symbol, e.g. Castor#2025!
DB_NAME=weather_db
```

> **ACR_NAME and POSTGRES_SERVER must be globally unique across all Azure accounts.**
> If creation fails with a conflict error, add a short suffix (e.g. `floridacastoracr2025`).

---

## Step 1 — Create a resource group

A resource group is a folder that holds all your Azure resources.

```bash
az group create --name $RESOURCE_GROUP --location $LOCATION
```

**Verify:** output includes `"provisioningState": "Succeeded"`.

---

## Step 2 — Create Azure Container Registry (ACR)

ACR stores your Docker image in Azure.

```bash
az acr create \
    --name $ACR_NAME \
    --resource-group $RESOURCE_GROUP \
    --sku Basic \
    --admin-enabled true
```

**Verify:**
```bash
az acr show --name $ACR_NAME --query loginServer -o tsv
# Expected: floridacastoracr.azurecr.io
```

---

## Step 3 — Build and push the Docker image

Run this from the project root (where the `Dockerfile` lives).

```bash
# Log in to your registry
az acr login --name $ACR_NAME

# Build
docker build -t $ACR_NAME.azurecr.io/floridacastor:latest .

# Push
docker push $ACR_NAME.azurecr.io/floridacastor:latest
```

**Verify:**
```bash
az acr repository list --name $ACR_NAME -o table
# Should show: floridacastor
```

---

## Step 4 — Create the PostgreSQL database server

This takes 3–5 minutes.

```bash
az postgres flexible-server create \
    --resource-group $RESOURCE_GROUP \
    --name $POSTGRES_SERVER \
    --location $LOCATION \
    --admin-user $DB_ADMIN_USER \
    --admin-password $DB_ADMIN_PASSWORD \
    --sku-name Standard_B1ms \
    --tier Burstable \
    --version 16 \
    --database-name $DB_NAME \
    --public-access 0.0.0.0
```

`--public-access 0.0.0.0` allows connections from all Azure services (including Container Apps).

**Verify:**
```bash
az postgres flexible-server show \
    --name $POSTGRES_SERVER \
    --resource-group $RESOURCE_GROUP \
    --query state -o tsv
# Expected: Ready
```

---

## Step 5 — Initialize the database schema

The app needs two tables (`forecasts`, `predictions`). Run this **once**, before deploying.

**From your local machine** (requires `psql`):

```bash
DB_HOST=$POSTGRES_SERVER.postgres.database.azure.com

# Add a firewall rule so your laptop can reach the DB
MY_IP=$(curl -s ifconfig.me)
az postgres flexible-server firewall-rule create \
    --resource-group $RESOURCE_GROUP \
    --name $POSTGRES_SERVER \
    --rule-name allow-local \
    --start-ip-address $MY_IP \
    --end-ip-address $MY_IP

# Run the schema
PGPASSWORD=$DB_ADMIN_PASSWORD psql \
    "host=$DB_HOST dbname=$DB_NAME user=$DB_ADMIN_USER sslmode=require" \
    < db/schema.sql
```

**Verify:**
```bash
PGPASSWORD=$DB_ADMIN_PASSWORD psql \
    "host=$DB_HOST dbname=$DB_NAME user=$DB_ADMIN_USER sslmode=require" \
    --command "\dt"
# Should list: forecasts, predictions
```

> **Don't have psql locally?** Use [Azure Cloud Shell](https://shell.azure.com):
> open the link in your browser, upload `db/schema.sql` using the upload button,
> then run the `psql` command above (Cloud Shell already has psql and your Azure credentials).

---

## Step 6 — Create the Container Apps environment

```bash
az containerapp env create \
    --name $ENVIRONMENT \
    --resource-group $RESOURCE_GROUP \
    --location $LOCATION
```

**Verify:**
```bash
az containerapp env show \
    --name $ENVIRONMENT \
    --resource-group $RESOURCE_GROUP \
    --query properties.provisioningState -o tsv
# Expected: Succeeded
```

---

## Step 7 — Deploy the Container App

First, build the connection string and fetch the ACR password:

```bash
DATABASE_URL="postgresql+psycopg2://${DB_ADMIN_USER}:${DB_ADMIN_PASSWORD}@${POSTGRES_SERVER}.postgres.database.azure.com/${DB_NAME}?sslmode=require"

ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query passwords[0].value -o tsv)
```

Deploy — `DATABASE_URL` is stored as a **secret** so the password never appears in logs:

```bash
az containerapp create \
    --name $APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --environment $ENVIRONMENT \
    --image $ACR_NAME.azurecr.io/floridacastor:latest \
    --registry-server $ACR_NAME.azurecr.io \
    --registry-username $ACR_NAME \
    --registry-password $ACR_PASSWORD \
    --target-port 5000 \
    --ingress external \
    --min-replicas 1 \
    --max-replicas 3 \
    --secrets db-url="$DATABASE_URL" \
    --env-vars DATABASE_URL=secretref:db-url FLASK_DEBUG=0
```

> `--secrets db-url="$DATABASE_URL"` saves the connection string as an Azure secret.
> `DATABASE_URL=secretref:db-url` injects it into the container at runtime without exposing it in shell history or Azure logs.

---

## Step 8 — Verify the deployment

```bash
# Get the public URL assigned by Azure
APP_URL=$(az containerapp show \
    --name $APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --query properties.configuration.ingress.fqdn -o tsv)

echo "https://$APP_URL"
```

Test the health endpoints:

```bash
# App process is running
curl https://$APP_URL/health
# Expected: {"status":"ok"}

# Database connection is working
curl https://$APP_URL/health/db
# Expected: {"status":"ok","database":"connected","select_1":1}

# Open the UI in your browser
open https://$APP_URL
```

Both checks passing means the app is live and connected to the database.

---

## Step 9 — Updating the app

After any code change:

```bash
# Rebuild and push
docker build -t $ACR_NAME.azurecr.io/floridacastor:latest .
docker push $ACR_NAME.azurecr.io/floridacastor:latest

# Trigger a new revision in Container Apps
az containerapp update \
    --name $APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --image $ACR_NAME.azurecr.io/floridacastor:latest
```

---

## Environment variables reference

| Variable | How it's set | Notes |
|----------|-------------|-------|
| `DATABASE_URL` | Azure secret `db-url` | Full connection string — always include `?sslmode=require` |
| `FLASK_DEBUG` | env var | Always `0` in production |
| `PORT` | `ENV PORT=5000` in Dockerfile | Already set — do not override |

To update the database secret after deployment:

```bash
az containerapp secret set \
    --name $APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --secrets db-url="$NEW_DATABASE_URL"

# Then restart to pick up the new secret
az containerapp revision restart \
    --name $APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --revision $(az containerapp revision list --name $APP_NAME \
        --resource-group $RESOURCE_GROUP --query "[0].name" -o tsv)
```

---

## Troubleshooting

### See live container logs

```bash
az containerapp logs tail \
    --name $APP_NAME \
    --resource-group $RESOURCE_GROUP
```

### Common failure points

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| ACR creation fails | `ACR_NAME` is already taken globally | Add a suffix: `floridacastoracr2025` |
| PostgreSQL creation fails | `POSTGRES_SERVER` is already taken globally | Add a suffix: `floridacastor-db-2025` |
| PostgreSQL creation fails with password error | Password doesn't meet complexity rules | Use uppercase + number + symbol: `Castor#2025!` |
| `/health/db` returns `"status":"error"` | `sslmode=require` missing or wrong connection string | Check `DATABASE_URL` includes `?sslmode=require` |
| `/health/db` returns `"status":"error"` | DB firewall blocks Container Apps | Confirm `--public-access 0.0.0.0` was set at creation |
| Container won't start (0 replicas running) | Image broken or `DATABASE_URL` missing | Check `az containerapp logs tail` |
| 502 on `/forecast` or `/recommend` | NWS API timeout or rate limit | Transient — retry. Gunicorn timeout is 120 s |
| Schema missing | `forecasts`/`predictions` tables not created | Re-run Step 5 |

### Container starts but `/health/db` fails

The most common issue. Debug in order:

1. Confirm the secret was set: `az containerapp secret list --name $APP_NAME --resource-group $RESOURCE_GROUP`
2. Check the server FQDN: must be `<server-name>.postgres.database.azure.com`
3. Check SSL: `sslmode=require` must be in the connection string
4. Check firewall: `az postgres flexible-server firewall-rule list --name $POSTGRES_SERVER --resource-group $RESOURCE_GROUP`

---

## Local development (unchanged)

```bash
docker compose up --build
# App: http://localhost:5001
# Uses local PostgreSQL container (not Azure)
```

`docker-compose.yml` is for local development only. Azure uses its own managed database.
