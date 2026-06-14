#!/bin/bash
set -e

RESOURCE_GROUP=floridacastor-rg
LOCATION=centralus
ACR_NAME=floridacastoracr
ENVIRONMENT=floridacastor-env
APP_NAME=floridacastor
POSTGRES_SERVER=floridacastor-db
DB_ADMIN_USER=weatheradmin
DB_ADMIN_PASSWORD='Castor#2025!'
DB_NAME=weather_db

if [ "${1}" != "--resume" ] && [ "${1}" != "--resume-from-db" ]; then
    echo "==> Step 2: Creating Azure Container Registry..."
    az acr create \
        --name $ACR_NAME \
        --resource-group $RESOURCE_GROUP \
        --sku Basic \
        --admin-enabled true
    echo "ACR created."

    echo ""
    echo "==> Step 3: Logging in to ACR and building image..."
    az acr login --name $ACR_NAME
    docker build --platform linux/amd64 -t $ACR_NAME.azurecr.io/floridacastor:latest .
    docker push $ACR_NAME.azurecr.io/floridacastor:latest
    echo "Image pushed."
fi

echo ""
if [ "${1}" == "--resume-from-db" ]; then
    echo "==> Step 4: Skipping server creation (already created via portal)..."
else
echo "==> Step 4: Creating PostgreSQL server (this takes 3-5 minutes)..."
az postgres flexible-server create \
    --resource-group $RESOURCE_GROUP \
    --name $POSTGRES_SERVER \
    --location $LOCATION \
    --admin-user $DB_ADMIN_USER \
    --admin-password $DB_ADMIN_PASSWORD \
    --sku-name Standard_B1ms \
    --tier Burstable \
    --version 16 \
    --public-access 0.0.0.0
echo "PostgreSQL server ready. Creating database..."
az postgres flexible-server db create \
    --resource-group $RESOURCE_GROUP \
    --server-name $POSTGRES_SERVER \
    --database-name $DB_NAME
echo "PostgreSQL ready."
fi

echo ""
echo "==> Step 5: Initializing database schema..."
echo "Creating database weather_db..."
az postgres flexible-server db create \
    --resource-group $RESOURCE_GROUP \
    --server-name $POSTGRES_SERVER \
    --name $DB_NAME
DB_HOST=$POSTGRES_SERVER.postgres.database.azure.com
MY_IP=$(curl -s ifconfig.me)
az postgres flexible-server firewall-rule create \
    --resource-group $RESOURCE_GROUP \
    --server-name $POSTGRES_SERVER \
    --name allow-local \
    --start-ip-address $MY_IP \
    --end-ip-address $MY_IP
PGPASSWORD=$DB_ADMIN_PASSWORD psql \
    "host=$DB_HOST dbname=$DB_NAME user=$DB_ADMIN_USER sslmode=require" \
    < db/schema.sql
echo "Schema initialized."

echo ""
echo "==> Step 6: Creating Container Apps environment..."
az containerapp env create \
    --name $ENVIRONMENT \
    --resource-group $RESOURCE_GROUP \
    --location $LOCATION
echo "Environment ready."

echo ""
echo "==> Step 7: Deploying Container App..."
DATABASE_URL="postgresql+psycopg2://${DB_ADMIN_USER}:${DB_ADMIN_PASSWORD}@${POSTGRES_SERVER}.postgres.database.azure.com/${DB_NAME}?sslmode=require"
ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query passwords[0].value -o tsv)

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

echo ""
echo "==> Done! Getting your app URL..."
APP_URL=$(az containerapp show \
    --name $APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --query properties.configuration.ingress.fqdn -o tsv)

echo ""
echo "============================================"
echo "App URL: https://$APP_URL"
echo "Health:  https://$APP_URL/health"
echo "DB check: https://$APP_URL/health/db"
echo "============================================"
