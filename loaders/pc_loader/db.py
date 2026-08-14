import re
from sqlalchemy import text


def _normalize(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(name).lower().strip()).strip("_")


def upsert_source(conn, nom: str, type_: str, description: str = None) -> int:
    nom = nom.lower().strip()   # normalize to avoid aurea/AUREA duplicates
    row = conn.execute(text("""
        INSERT INTO raw.pc_source (nom, type, description)
        VALUES (:nom, :type, :desc)
        ON CONFLICT (nom) DO UPDATE SET type = EXCLUDED.type
        RETURNING id
    """), {"nom": nom, "type": type_, "desc": description}).fetchone()
    return row[0]


def upsert_echantillon(conn, code: str, meta: dict, source_id: int) -> int:
    row = conn.execute(text("""
        INSERT INTO raw.pc_echantillon
            (code_echantillon, aurea_id, date_prelevement, localisation,
             culture, type_sol, client_code, source_id)
        VALUES (:code, :aurea_id, :date_prel, :localisation,
                :culture, :type_sol, :client_code, :source_id)
        ON CONFLICT (code_echantillon, source_id)
        DO UPDATE SET
            date_prelevement = EXCLUDED.date_prelevement,
            localisation     = EXCLUDED.localisation,
            culture          = EXCLUDED.culture,
            type_sol         = EXCLUDED.type_sol,
            client_code      = EXCLUDED.client_code
        RETURNING id
    """), {
        "code":         code,
        "aurea_id":     meta.get("aurea_id"),
        "date_prel":    meta.get("date_prelevement"),
        "localisation": meta.get("localisation"),
        "culture":      meta.get("culture"),
        "type_sol":     meta.get("type_sol"),
        "client_code":  meta.get("client_code"),
        "source_id":    source_id,
    }).fetchone()
    return row[0]


def upsert_parametre(conn, param_ids: dict, libelle: str,
                      nom_court: str = None, categorie: str = None) -> int:
    nom_norm = _normalize(libelle)
    if nom_norm in param_ids:
        return param_ids[nom_norm]
    row = conn.execute(text("""
        INSERT INTO raw.pc_parametre (nom, nom_normalise, description, categorie)
        VALUES (:nom, :norm, :desc, :cat)
        ON CONFLICT (nom_normalise) DO UPDATE SET
            nom       = EXCLUDED.nom,
            categorie = COALESCE(EXCLUDED.categorie, raw.pc_parametre.categorie)
        RETURNING id
    """), {
        "nom":  libelle,
        "norm": nom_norm,
        "desc": nom_court if nom_court and nom_court != libelle else None,
        "cat":  categorie or None,
    }).fetchone()
    param_ids[nom_norm] = row[0]
    return row[0]


def upsert_mesure(conn, ech_id: int, param_id: int, source_id: int,
                   valeur_num, valeur_txt, unite, date_mesure) -> None:
    conn.execute(text("""
        INSERT INTO raw.pc_mesure
            (echantillon_id, parametre_id, source_id, valeur, valeur_texte, unite, date_mesure)
        VALUES (:ech, :param, :src, :val, :val_txt, :unite, :date)
        ON CONFLICT (echantillon_id, parametre_id, source_id)
        DO UPDATE SET
            valeur       = EXCLUDED.valeur,
            valeur_texte = EXCLUDED.valeur_texte,
            unite        = EXCLUDED.unite,
            date_mesure  = EXCLUDED.date_mesure
    """), {
        "ech":     ech_id,
        "param":   param_id,
        "src":     source_id,
        "val":     valeur_num,
        "val_txt": valeur_txt,
        "unite":   unite,
        "date":    date_mesure,
    })
