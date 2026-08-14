"""
Fix PRAS coordinates with real geographic data
Uses French department centroids
"""

# Real coordinates by department (postal code)
DEPT_COORDS = {
    # Alsace
    "67": (48.5, 7.6),
    "68": (47.8, 7.3),
    # Lorraine
    "54": (48.7, 6.0),
    "55": (49.0, 5.5),
    "57": (49.1, 6.2),
    "88": (48.2, 6.5),
    # Bourgogne-Franche-Comté
    "21": (47.3, 4.5),
    "25": (47.2, 6.0),
    "39": (46.6, 5.7),
    "58": (47.2, 3.3),
    "71": (46.5, 4.5),
    "89": (47.8, 3.6),
    "90": (47.6, 6.8),
    # Auvergne-Rhône-Alpes
    "01": (46.3, 5.3),
    "03": (46.3, 3.5),
    "07": (45.2, 4.6),
    "15": (45.0, 2.9),
    "26": (44.8, 5.1),
    "38": (45.2, 5.7),
    "42": (45.4, 4.1),
    "43": (45.1, 3.9),
    "63": (45.8, 3.1),
    "69": (45.8, 4.8),
    "73": (45.5, 6.2),
    "74": (46.0, 6.5),
    # Provence-Alpes-Côte d'Azur
    "04": (44.0, 6.0),
    "05": (44.7, 6.2),
    "06": (44.0, 7.3),
    "13": (43.5, 5.3),
    "83": (43.4, 6.4),
    "84": (44.2, 5.0),
    # Languedoc-Roussillon
    "11": (43.3, 2.4),
    "30": (44.1, 4.3),
    "34": (43.6, 3.5),
    "48": (44.7, 3.9),
    "66": (42.6, 2.7),
    # Occitanie
    "09": (43.0, 1.5),
    "12": (44.5, 2.6),
    "31": (43.6, 1.4),
    "32": (43.7, 0.4),
    "46": (44.5, 1.4),
    "65": (43.2, 0.1),
    "81": (44.1, 2.2),
    "82": (44.2, 1.4),
    # Aquitaine-Limousin-Poitou-Charentes
    "16": (45.7, 0.2),
    "17": (45.7, -0.7),
    "19": (45.5, 1.5),
    "23": (46.1, 2.4),
    "24": (45.2, 0.8),
    "33": (44.8, -0.6),
    "40": (43.9, -0.8),
    "47": (44.4, 0.6),
    "64": (43.3, -0.4),
    "79": (46.4, -0.4),
    "86": (46.6, 0.9),
    "87": (45.9, 1.3),
    # Pays de la Loire
    "44": (47.4, -1.5),
    "49": (47.4, -0.5),
    "53": (48.3, -0.6),
    "72": (48.0, 0.2),
    "85": (46.7, -1.4),
    # Bretagne
    "22": (48.5, -2.8),
    "29": (48.4, -4.1),
    "35": (48.1, -1.7),
    "56": (47.7, -3.4),
    # Normandie
    "14": (49.3, -0.4),
    "27": (49.0, 1.1),
    "50": (49.4, -1.5),
    "61": (48.5, 0.2),
    "76": (49.5, 1.1),
    # Hauts-de-France
    "02": (49.6, 3.9),
    "59": (50.6, 3.1),
    "60": (49.4, 2.4),
    "62": (50.4, 2.1),
    "80": (50.1, 2.3),
    # Île-de-France
    "75": (48.9, 2.4),
    "77": (48.6, 3.1),
    "78": (48.8, 1.8),
    "91": (48.6, 2.4),
    "92": (48.8, 2.3),
    "93": (48.9, 2.5),
    "94": (48.8, 2.5),
    "95": (49.0, 2.1),
    # Centre-Val de Loire
    "18": (47.1, 2.3),
    "28": (48.4, 1.5),
    "36": (46.9, 1.7),
    "37": (47.4, 0.9),
    "41": (47.6, 1.3),
    "45": (48.2, 2.4),
}


def get_corrected_coordinates(pra_name):
    """
    Return corrected coordinates for a PRAS station
    Extracts department code from name (last 2 digits)
    """
    import re

    # Extract department code from last characters
    match = re.search(r"(\d{2})$", pra_name)
    if match:
        dept_code = match.group(1)
        if dept_code in DEPT_COORDS:
            return DEPT_COORDS[dept_code]

    # Otherwise return None (will keep original coordinates)
    return None


def apply_coordinate_fixes(pras_list):
    """
    Apply coordinate corrections to PRAS list
    """
    corrected = []
    for pra in pras_list:
        pra_copy = pra.copy()
        coords = get_corrected_coordinates(pra["name"])
        if coords:
            pra_copy["latitude"], pra_copy["longitude"] = coords
        corrected.append(pra_copy)

    return corrected
