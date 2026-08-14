-- Migration 007: recalculating is_pathogen with the list validated by Marion (54 genera)
-- Old logic: 20 heuristic genera
-- New logic: 54 genera validated by Marion (2026-03-30)
UPDATE raw.metag_otu_abundance
SET is_pathogen = LOWER(taxon_genus) = ANY(ARRAY[
    'fusarium', 'rhizoctonia', 'pythium', 'phytophthora', 'sclerotinia',
    'verticillium', 'botrytis', 'alternaria', 'gaeumannomyces', 'plasmodiophora',
    'colletotrichum', 'pyrenophora', 'septoria', 'puccinia', 'blumeria',
    'erysiphe', 'magnaporthe', 'sclerotium', 'macrophomina', 'thielaviopsis',
    'chondrostereum', 'cicinobolus', 'claviceps', 'cristulariella',
    'didymella', 'diplocarpon', 'exobasidium', 'fomitopsis',
    'guignardia', 'helicobasidium', 'heterobasidion', 'kabatiella',
    'leptosphaeria', 'leveillula', 'marasmius', 'monilinia',
    'ophiostoma', 'peyronellaea', 'phomopsis', 'phragmidium',
    'podosphaera', 'rhytisma', 'rosellinia', 'sphacelotheca',
    'sporisorium', 'stromatinia', 'taphrina', 'thanatephorus',
    'tilletia', 'tranzschelia', 'uromyces', 'urocystis',
    'ustilago', 'venturia'
])
WHERE taxon_genus IS NOT NULL;
