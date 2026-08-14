import argparse

from .excel_export import generate_donnees_source, generate_reporting_mensuel
from .sharepoint_upload import (
    PATH_DONNEES_SOURCE,
    PATH_REPORTING_MENSUEL,
    upload_to_sharepoint,
)


def main():
    parser = argparse.ArgumentParser(description="Excel export to SharePoint")
    parser.add_argument(
        "--mode",
        choices=["donnees-source", "reporting-mensuel"],
        required=True,
        help="donnees-source: every thursday export | reporting-mensuel: end-of-month export",
    )
    args = parser.parse_args()

    if args.mode == "donnees-source":
        content, filename = generate_donnees_source()
        upload_to_sharepoint(content, filename, PATH_DONNEES_SOURCE)
    else:
        content, filename = generate_reporting_mensuel()
        upload_to_sharepoint(content, filename, PATH_REPORTING_MENSUEL)


if __name__ == "__main__":
    main()
