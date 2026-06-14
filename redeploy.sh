#!/bin/bash
az containerapp update \
    --name floridacastor \
    --resource-group floridacastor-rg \
    --image floridacastoracr.azurecr.io/floridacastor:latest
