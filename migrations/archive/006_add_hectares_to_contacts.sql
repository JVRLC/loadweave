-- Migration 006 : suppression raw.contacts pour recréation avec x_myco_total_hectares
-- La table sera recréée automatiquement au prochain run du business loader

DROP TABLE IF EXISTS raw.contacts;
