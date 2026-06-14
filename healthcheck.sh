#!/bin/bash
echo "==> App health:"
curl -s https://floridacastor.graypond-6ab7b932.centralus.azurecontainerapps.io/health

echo ""
echo "==> Database health:"
curl -s https://floridacastor.graypond-6ab7b932.centralus.azurecontainerapps.io/health/db
echo ""
