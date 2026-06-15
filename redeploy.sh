#!/bin/bash
# Build the current code into a uniquely-tagged image, push it to ACR, and roll
# the Container App onto it. The timestamp tag guarantees a fresh revision every
# time (re-pushing :latest can leave Azure serving the old image).
set -e

ACR_NAME=floridacastoracr
RESOURCE_GROUP=floridacastor-rg
APP_NAME=floridacastor
IMAGE_REPO=$ACR_NAME.azurecr.io/floridacastor
TAG=$(date +%Y%m%d-%H%M%S)

echo "==> Building $IMAGE_REPO:$TAG ..."
az acr login --name $ACR_NAME
docker build --platform linux/amd64 -t "$IMAGE_REPO:$TAG" .

echo "==> Pushing image ..."
docker push "$IMAGE_REPO:$TAG"

echo "==> Rolling $APP_NAME onto new image ..."
az containerapp update \
    --name $APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --image "$IMAGE_REPO:$TAG"

echo "==> Done. Active revision:"
az containerapp revision list \
    --name $APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --query "[?properties.active].{revision:name, image:properties.template.containers[0].image}" \
    -o table
