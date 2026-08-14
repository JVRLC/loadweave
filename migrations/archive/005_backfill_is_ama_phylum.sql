-- Migration 005: recompute is_ama based on taxon_phylum = 'Glomeromycota'
-- Previous logic: genus IN AMA_GENERA (static list)
-- New logic: taxon_phylum = 'Glomeromycota' (validated by Greg)
UPDATE raw.metag_otu_abundance
SET is_ama = (taxon_phylum = 'Glomeromycota')
WHERE is_ama != (taxon_phylum = 'Glomeromycota')
   OR (is_ama IS NULL AND taxon_phylum IS NOT NULL);
