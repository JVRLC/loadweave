import requests
import time
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from loaders.weather_loader.history.models import MeteoData
from loaders.weather_loader.history.config import (
    API_URL,
    API_DELAY,
)


class OpenMeteoClient:
    def __init__(self, base_url=API_URL, delay=API_DELAY):
        self.base_url = base_url
        self.session = requests.Session()

        # Robust configuration for connection retries (DNS, timeouts, server errors)
        retry_strategy = Retry(
            total=5,
            backoff_factor=2,  # Exponential backoff: 2s, 4s, 8s...
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        self.delay = delay
        self.locations = []  # Initialize locations list

    def get_historical_data(
        self, latitude, longitude, location_name, start_date, end_date, code_pra=None
    ):
        # NASA POWER API Parameters (Monthly)
        # T2M_MIN: Temperature Min at 2 Meters
        # T2M_MAX: Temperature Max at 2 Meters
        # PRECTOTCORR: Precipitation (Corrected)
        # ALLSKY_SFC_SW_DWN: All Sky Surface Shortwave Downward Irradiance
        # WS10M_MAX: Wind Speed Max at 10 Meters
        # ET0: Reference Evapotranspiration (FAO-56) - Often available in monthly

        params = {
            "parameters": "T2M_MIN,T2M_MAX,PRECTOTCORR,ALLSKY_SFC_SW_DWN,WS10M_MAX",
            "community": "AG",
            "longitude": longitude,
            "latitude": latitude,
            "start": start_date.year,
            "end": end_date.year,
            "format": "JSON",
        }

        max_retries = 5
        retry_count = 0

        while retry_count < max_retries:
            try:
                resp = self.session.get(self.base_url, params=params, timeout=60)

                if resp.status_code == 422:
                    # 422 Unprocessable Entity
                    # Strategy: Try reducing the end year (future dates issue)
                    current_end = params["end"]
                    if current_end > params["start"]:
                        print(
                            f"⚠ NASA 422: Reducing end year from {current_end} to {current_end - 1}"
                        )
                        params["end"] = current_end - 1
                        time.sleep(1)
                        continue
                    else:
                        print(
                            f"✗ NASA 422: Cannot reduce year further (Start={params['start']}, End={current_end})"
                        )
                        return []

                if resp.status_code == 429:
                    wait_time = 60 * (retry_count + 1)  # Wait 1 min, 2 mins, etc.
                    print(f"⚠ NASA 429 (Rate Limit): Waiting {wait_time}s...")
                    time.sleep(wait_time)
                    retry_count += 1
                    continue

                if resp.status_code != 200:
                    print(f"⚠ NASA API Error {resp.status_code} pour {location_name}")
                    time.sleep(2)
                    retry_count += 1
                    continue

                data = resp.json()

                if not data.get("properties") or not data["properties"].get(
                    "parameter"
                ):
                    print(f"✗ Invalid NASA data for {location_name}")
                    return []

                result = self._parse_nasa(
                    data, location_name, latitude, longitude, code_pra
                )
                time.sleep(self.delay)
                return result

            except Exception as e:
                print(f"✗ NASA network error for {location_name}: {e}")
                time.sleep(5)
                retry_count += 1

        print(f"✗ GIVING UP NASA for {location_name} after {max_retries} attempts.")
        return []

    def _parse_nasa(self, data, location_name, latitude, longitude, code_pra=None):
        meteo_list = []
        properties = data.get("properties", {}).get("parameter", {})

        # Keys are now years (e.g., "2020") or "ANN"
        # But for MONTHLY endpoint, structure is often:
        # properties['T2M_MIN']['202001'] = val
        # properties['T2M_MIN']['202002'] = val
        # ...
        # properties['T2M_MIN']['202013'] = val (Annual average sometimes)

        # Get all date keys (YYYYMM)
        # Filter to keep only 6-digit numeric keys (YYYYMM)
        sample_keys = properties.get("T2M_MIN", {}).keys()
        dates_keys = sorted([k for k in sample_keys if k.isdigit() and len(k) == 6])

        if not dates_keys:
            return meteo_list

        for date_str in dates_keys:
            try:
                # date_str is YYYYMM
                year = int(date_str[:4])
                month = int(date_str[4:])

                # Create a dummy date at the 1st of the month
                d = datetime(year, month, 1)

                # Extract values
                def get_val(key):
                    val = properties.get(key, {}).get(date_str)
                    return val if val is not None and val != -999 else None

                tmin = get_val("T2M_MIN")
                tmax = get_val("T2M_MAX")
                precip = get_val("PRECTOTCORR")  # mm/day average usually
                rad = get_val("ALLSKY_SFC_SW_DWN")  # kWh/m^2/day
                wind = get_val("WS10M_MAX")  # m/s

                # Rad Conversion: kWh/m2/day -> MJ/m2/day
                if rad is not None:
                    rad = rad * 3.6

                # Calculate Kc
                kc = self._calculate_kc(month, tmax)  # tmax is monthly average of max

                meteo_list.append(
                    MeteoData(
                        latitude=latitude,
                        longitude=longitude,
                        location_name=location_name,
                        code_pra=code_pra,
                        date_debut_releve=d.date(),
                        date_fin_releve=d.date(),
                        mois_observe=month,
                        annee_observee=year,
                        temperature_min_moyenne=tmin,
                        temperature_max_moyenne=tmax,
                        precipitation_moyenne=precip,
                        coefficient_kc=kc,
                        vitesse_max_moyenne_vent=wind,
                        rayonnement_solaire_moyen=rad,
                    )
                )

            except ValueError:
                continue

        print(f"✓ NASA: {len(meteo_list)} months retrieved for {location_name}")
        return meteo_list


    def _calculate_kc(self, month, temperature):
        """
        Calculate Kc based on growth stage and temperature.
        FAO-56 method: Kc varies through the growing season.

        Typical crop cycle in France (cereals):
        - Initial stage (Nov-Dec): Kc = 0.3-0.4 (seedling)
        - Development stage (Jan-Feb): Kc = 0.4-0.7 (vegetative growth)
        - Mid season (Mar-Apr-May): Kc = 0.8-1.1 (flowering, pod filling)
        - Late season (Jun-Jul): Kc = 0.8-1.0 (ripening)
        - Harvest (Aug-Sep): Kc = 0.3-0.5 (maturity, senescence)
        - Off season (Oct): Kc = 0.3 (dormant)
        """
        # Base Kc by month (typical cereal crop in France)
        kc_by_month = {
            1: 0.4,  # January - Early development
            2: 0.5,  # February - Development
            3: 0.75,  # March - Mid-season beginning
            4: 1.05,  # April - Peak season
            5: 1.1,  # May - Peak season
            6: 0.9,  # June - Late season
            7: 0.7,  # July - Late season/Ripening
            8: 0.4,  # August - Late season/Maturity
            9: 0.3,  # September - Harvest
            10: 0.3,  # October - Off-season
            11: 0.3,  # November - Off-season
            12: 0.35,  # December - Initial stage
        }

        # Get base Kc for the month
        base_kc = kc_by_month.get(month, 0.3)

        # Adjust Kc based on temperature
        # Higher temperatures increase water demand
        temp_factor = 1.0
        if temperature is not None:
            if temperature < 0:
                temp_factor = 0.5  # Frozen/dormant
            elif temperature < 5:
                temp_factor = 0.7  # Cold
            elif temperature > 30:
                temp_factor = 1.15  # Hot, higher water stress
            else:
                # Linear adjustment between 5°C and 30°C
                temp_factor = 0.85 + (temperature - 5) / 25 * 0.3

        kc = base_kc * temp_factor
        # Ensure Kc stays within reasonable bounds
        return min(max(kc, 0.2), 1.3)

    def get_locations(self):
        return self.locations

    def close(self):
        if self.session:
            self.session.close()
