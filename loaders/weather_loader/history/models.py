from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class MeteoData:
    latitude: float
    longitude: float
    location_name: str = None
    code_pra: str = None
    date_debut_releve: datetime = None
    date_fin_releve: datetime = None
    mois_observe: int = None
    annee_observee: int = None
    temperature_min_moyenne: float = None
    temperature_max_moyenne: float = None
    precipitation_moyenne: float = None
    coefficient_kc: float = None
    vitesse_max_moyenne_vent: float = None
    rayonnement_solaire_moyen: float = None
    loaded_at: datetime = field(default_factory=datetime.now)
