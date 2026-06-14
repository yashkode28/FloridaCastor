#!/bin/bash
az containerapp show --name floridacastor --resource-group floridacastor-rg --query "properties.configuration.ingress.fqdn" -o tsv
