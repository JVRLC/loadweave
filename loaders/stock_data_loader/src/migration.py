from loaders.business_data_loader.src.migration import migrate_model
from loaders.o2dw import setup_database
from loaders.stock_data_loader.src.config_model import STOCK_MODELS_CONFIG


def mig_insert():
    engine = setup_database()

    for cfg in STOCK_MODELS_CONFIG:
        migrate_model(engine, cfg)

    print("STOCK MIGRATION COMPLETE")


if __name__ == "__main__":
    mig_insert()
