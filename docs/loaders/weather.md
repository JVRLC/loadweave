# Météo

Deux loaders distincts alimentent les données météorologiques depuis des APIs publiques.

## Sources

| Loader | API | Données | Fréquence |
|---|---|---|---|
| `weather-history` | [NASA POWER](https://power.larc.nasa.gov) | Historique mensuel | Hebdomadaire |
| `weather-daily` | [Open-Meteo](https://open-meteo.com) | Données journalières | Quotidienne |

## Data flow

```mermaid
flowchart LR
    NASA["NASA POWER API\ntemporal/monthly/point"]
    OM["Open-Meteo API\nforecast / archive"]

    NASA -->|"coords (lat, lon) par PRA"| WH["weather-history-loader"]
    OM -->|"coords (lat, lon) par PRA"| WD["weather-daily-loader"]

    WH --> DB1[("raw.weather_history")]
    WD --> DB2[("raw.weather_daily")]
```

## Run

=== "Production"

    ```bash
    make up SERVICE=weather-history ENV=prod
    make up SERVICE=weather-daily ENV=prod
    ```

=== "Développement"

    ```bash
    make up SERVICE=weather-history ENV=dev
    make up SERVICE=weather-daily ENV=dev
    ```
