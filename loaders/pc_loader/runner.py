import logging
from loaders.pc_loader.base import BasePCLoader
from loaders.pc_loader.db import upsert_source, upsert_echantillon, upsert_parametre, upsert_mesure
from loaders.db import get_engine
logger = logging.getLogger(__name__)


def run(loader: BasePCLoader) -> None:
    engine     = get_engine()
    param_ids:  dict[str, int] = {}
    source_ids: dict[str, int] = {}   
    total_ech  = 0
    total_mes  = 0

    
    with engine.begin() as conn:
        default_source_id = upsert_source(
            conn, loader.source_name, loader.source_type, loader.source_description
        )
        source_ids[loader.source_name] = default_source_id
        logger.info("Source '%s' → id=%d", loader.source_name, default_source_id)

    for item in loader.iter_items():
        if not item.get("mesures"):
            continue

        item_source = item.get("source")
        with engine.begin() as conn:
            if item_source:
                nom = item_source["nom"]
                if nom not in source_ids:
                    source_ids[nom] = upsert_source(
                        conn, nom, item_source["type"], item_source.get("description")
                    )
                    logger.info("Source '%s' → id=%d", nom, source_ids[nom])
                source_id = source_ids[nom]
            else:
                source_id = default_source_id

            ech_id = upsert_echantillon(conn, item["code"], item["meta"], source_id)

            for m in item["mesures"]:
                libelle = m.get("libelle") or ""
                if not libelle:
                    continue

                valeur = m.get("valeur")
                try:
                    valeur_num = float(valeur) if valeur is not None else None
                    valeur_txt = None
                except (ValueError, TypeError):
                    valeur_num = None
                    valeur_txt = str(valeur)

                param_id = upsert_parametre(conn, param_ids, libelle, m.get("nom_court"), m.get("categorie"))
                upsert_mesure(conn, ech_id, param_id, source_id,
                              valeur_num, valeur_txt, m.get("unite"), m.get("date_mesure"))
                total_mes += 1

        total_ech += 1

    logger.info("✓ %d samples, %d measures loaded", total_ech, total_mes)
    engine.dispose()
