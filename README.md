# FloridaCastor

**Live app:** https://floridacastor.graypond-6ab7b932.centralus.azurecontainerapps.io

A Florida outdoor weather risk advisor. Select any major Florida city to get a 24-hour risk assessment — **Good**, **Caution**, or **No-go** — based on real-time weather data from the National Weather Service.

Florida weather can change quickly throughout the year, especially during the wet and hurricane seasons. While most weather apps provide basic information such as temperature and precipitation, it is often difficult to understand how multiple weather factors combine to affect outdoor safety and comfort.

FloridaCastor goes beyond the forecast by analyzing conditions such as heat, humidity, wind, precipitation, thunderstorms, and seasonal weather patterns to generate a simple outdoor risk assessment. Users receive a calculated risk score and a recommendation—Good, Caution, or No-go—along with insights into the factors contributing to the overall risk level.

## What it does

- Fetches live hourly forecasts for 10 Florida cities
- Runs a feature engineering pipeline (heat index, precipitation, wind, storm signals)
- Produces a risk score (0–100) and a plain-English recommendation
- Displays a 24-hour timeline with per-hour risk labels

## Tech stack

- **Backend:** Python, Flask, Gunicorn
- **ML pipeline:** pandas, scikit-learn, NumPy
- **Database:** PostgreSQL (SQLAlchemy)
- **Frontend:** Vanilla HTML/CSS/JS
- **Infrastructure:** Docker, Azure Container Apps, Azure Database for PostgreSQL

## Running locally

```bash
docker compose up --build
# App: http://localhost:5001
```

## Deployment

Deployed to Azure Container Apps. See [DEPLOY_AZURE.md](DEPLOY_AZURE.md) for the full deployment guide.

## Updating the live app

After any code change:

```bash
docker build --platform linux/amd64 -t floridacastoracr.azurecr.io/floridacastor:latest .
docker push floridacastoracr.azurecr.io/floridacastor:latest
./redeploy.sh
```

<img width="892" height="910" alt="image" src="https://github.com/user-attachments/assets/9316de8f-2c2b-4d38-b849-f7b2817105e4" />

