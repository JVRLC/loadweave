import logging

from loaders.stock_data_loader.src.migration import mig_insert


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    mig_insert()


if __name__ == "__main__":
    main()
