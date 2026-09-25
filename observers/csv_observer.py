import csv
import os

from observers.observer import Observateur


class CSVObserver(Observateur):

    def __init__(self, fichier="portfolio_log.csv"):
        self.fichier = fichier

    def actualiser(self, sujet) -> None:

        donnees = sujet.get_donnees()

        fichier_existe = os.path.exists(self.fichier)

        with open(
            self.fichier,
            "a",
            newline="",
            encoding="utf-8"
        ) as fichier:

            writer = csv.writer(fichier)

            if not fichier_existe:

                writer.writerow([
                    "horodatage",
                    "ticker",
                    "quantite",
                    "prix",
                    "variation",
                    "valeur"
                ])

            for ticker, infos in donnees["titres"].items():

                writer.writerow([
                    donnees["horodatage"],
                    ticker,
                    infos["quantite"],
                    infos["prix"],
                    infos["variation"],
                    infos["valeur"]
                ])