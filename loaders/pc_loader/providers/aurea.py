import argparse
import gc
import json
import logging
import os
from datetime import date
from typing import Iterator, Optional

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from loaders.pc_loader.base import BasePCLoader

load_dotenv()

logger = logging.getLogger(__name__)

BASE_URL = "https://online.aurea.eu"
LOGIN_URL = f"{BASE_URL}/resultats"
API_URL = f"{BASE_URL}/api/resultats.json"
PAGE_SIZE = 10

PHYSICO_MATRICES = {"SOL", "ENA", "EAV", "MFS", "MET", "RAN", "SRV"}


class AureaLoader(BasePCLoader):
    source_name = "aurea"
    source_type = "prestataire"
    source_description = "Portail analyses Aurea (online.aurea.eu)"

    def __init__(self):
        self._session = self._build_session()

    # Auth
    def _build_session(self) -> requests.Session:
        login = os.getenv("AUREA_LOGIN")
        password = os.getenv("AUREA_PASSWORD")
        if not login or not password:
            raise RuntimeError(
                "Variables AUREA_LOGIN et AUREA_PASSWORD manquantes.\n"
                "Ajoutez-les à votre fichier .env."
            )

        s = requests.Session()
        s.headers["User-Agent"] = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0"
        )

        r = s.get(LOGIN_URL, timeout=30)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        form = soup.find("form")
        if not form:
            raise RuntimeError("Formulaire de login introuvable.")

        payload = {
            i.get("name"): i.get("value", "")
            for i in form.find_all("input")
            if i.get("name")
        }
        payload["username"] = login
        payload["password"] = password

        r2 = s.post(f"{BASE_URL}/", data=payload, allow_redirects=True, timeout=30)
        r2.raise_for_status()

        if (
            "mes analyses" not in r2.text.lower()
            and "deconnexion" not in r2.text.lower()
        ):
            raise RuntimeError(
                "Connexion Aurea échouée — identifiants incorrects ou portail inaccessible."
            )

        logger.info("✓ Connecté au portail Aurea (url=%s)", r2.url)
        s.headers.update(
            {
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json, */*",
                "Referer": LOGIN_URL,
            }
        )
        return s

    # Pagination
    def _iter_pages(self):
        page = 1
        total_pages = None
        skipped: dict[str, int] = {}

        while True:
            r = self._session.get(
                API_URL, params={"page": page, "limit": PAGE_SIZE}, timeout=30
            )
            r.raise_for_status()
            data = r.json()
            r.close()
            del r

            payload = data["resultats"]
            if total_pages is None:
                total_pages = payload["pagination"]["totalPages"]
                logger.info(
                    "Aurea : %d résultats au total, %d pages",
                    payload["pagination"]["total"],
                    total_pages,
                )

            items = []
            for item in payload["data"]:
                mat = item.get("c_matiere", "")
                if mat not in PHYSICO_MATRICES:
                    skipped[mat] = skipped.get(mat, 0) + 1
                else:
                    items.append(item)

            del data
            logger.info(
                "  Page %d/%d — %d physico-chimiques", page, total_pages, len(items)
            )
            yield items

            if page >= total_pages:
                if skipped:
                    logger.info("Matrices exclues : %s", skipped)
                break
            page += 1

    # Parsing
    @staticmethod
    def _donnees_values(item: dict):
        donnees = item.get("resultats_donnees", [])
        return donnees.values() if isinstance(donnees, dict) else []

    @staticmethod
    def _parse_date(date_str: Optional[str]) -> Optional[date]:
        if not date_str:
            return None
        try:
            return date.fromisoformat(date_str[:10])
        except (ValueError, AttributeError):
            return None

    def _parse_item(self, item: dict) -> Optional[dict]:
        donnees = list(self._donnees_values(item))
        if not donnees:
            return None

        ref = (item.get("refechantillon") or "").strip()
        aurea_id = str(item["numresultat"])
        date_prel = self._parse_date(item.get("date_prelevement_brut"))

        mesures = []
        for d in donnees:
            libelle = (
                d.get("c_determ_libelle")
                or (d.get("determination") or {}).get("libelle_long")
                or ""
            )
            nom_court = (d.get("determination") or {}).get("libelle_court") or libelle
            unite = (
                (d.get("unites_sec") or {}).get("libelle_court") or ""
            ).strip() or None
            mesures.append(
                {
                    "libelle": libelle,
                    "nom_court": nom_court,
                    "valeur": d.get("resultat_sec"),
                    "unite": unite,
                    "date_mesure": date_prel,
                }
            )

        return {
            "code": ref if ref else aurea_id,
            "meta": {
                "aurea_id": aurea_id,
                "date_prelevement": date_prel,
                "localisation": (
                    item.get("libelle_site")
                    or item.get("libelle_site_txt_libre")
                    or item.get("libelle_point_prelevement")
                    or None
                ),
                "culture": None,
                "type_sol": (item.get("matiere") or {}).get("libelle")
                or item.get("c_matiere")
                or "",
                "client_code": (item.get("organisme") or {}).get("raison_sociale"),
            },
            "mesures": mesures,
        }

    # Interface BasePCLoader
    def iter_items(self) -> Iterator[dict]:
        for raw_items in self._iter_pages():
            for item in raw_items:
                parsed = self._parse_item(item)
                if parsed:
                    yield parsed
            del raw_items
            gc.collect()

    # Mode explore (diagnostic, sans BDD)
    def explore(self) -> None:
        r = self._session.get(API_URL, params={"page": 1, "limit": 5}, timeout=30)
        payload = r.json()["resultats"]
        pagination = payload["pagination"]
        items = payload["data"]

        print(f"\n{'═'*60}")
        print(f"AUREA — Portail {BASE_URL}")
        print(f"{'═'*60}")
        print(
            f"Total résultats : {pagination['total']}  |  Pages : {pagination['totalPages']}"
        )

        mats: dict[str, int] = {}
        for it in items:
            m = (it.get("matiere") or {}).get("libelle") or it.get("c_matiere") or "?"
            mats[m] = mats.get(m, 0) + 1
        print("\nMatières (page 1 seulement) :")
        for mat, count in sorted(mats.items(), key=lambda x: -x[1]):
            is_pc = any(
                it.get("c_matiere") in PHYSICO_MATRICES
                for it in items
                if (it.get("matiere") or {}).get("libelle") == mat
            )
            print(f"  {mat:<35} {count:>3}  {'✓ chargé' if is_pc else '✗ exclu'}")

        first = next((x for x in items if x.get("resultats_donnees")), None)
        if first:
            print(f"\nExemple (numresultat={first['numresultat']}) :")
            print(f"  refechantillon   : {first.get('refechantillon')}")
            print(f"  date_prelevement : {first.get('date_prelevement_brut', '')[:10]}")
            print(f"  matiere          : {(first.get('matiere') or {}).get('libelle')}")
            donnees = first["resultats_donnees"]
            print(f"\n  Paramètres mesurés ({len(donnees)}) :")
            for d in list(donnees.values())[:15]:
                val = d.get("resultat_sec")
                unite = (d.get("unites_sec") or {}).get("libelle_court", "").strip()
                print(f"    {d.get('c_determ_libelle'):40s}  {str(val):12s} {unite}")

        out = "/tmp/aurea_explore_result.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        print(f"\n{'═'*60}")
        print(f"Exemple sauvegardé → {out}")
        print(f"{'═'*60}")


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s — %(message)s")

    parser = argparse.ArgumentParser(
        description="Loader Aurea résultats physico-chimiques"
    )
    parser.add_argument(
        "--explore",
        action="store_true",
        help="Affiche la structure sans charger en BDD",
    )
    args = parser.parse_args()

    loader = AureaLoader()
    if args.explore:
        loader.explore()
    else:
        from loaders.pc_loader.runner import run

        logging.getLogger(__name__).info("=== Aurea loader ===")
        run(loader)


if __name__ == "__main__":
    main()
