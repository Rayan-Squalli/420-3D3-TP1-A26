from datetime import datetime

import yfinance as yf

from models.subject import Sujet


class PortfolioSujet(Sujet):

    def __init__(self, titres=None):
        super().__init__()

        self.titres = titres or {
            "AAPL": {
                "quantite": 10,
                "seuil_haut": 200.0,
                "seuil_bas": 150.0,
            },
            "GOOGL": {
                "quantite": 5,
                "seuil_haut": 160.0,
                "seuil_bas": 120.0,
            },
            "MSFT": {
                "quantite": 8,
                "seuil_haut": 430.0,
                "seuil_bas": 380.0,
            },
        }

        self.prix = {}
        self.ouvertures = {}
        self.derniere_mise_a_jour = None

    def get_donnees(self) -> dict:
        titres = {}

        valeur_totale = 0.0
        valeur_ouverture = 0.0

        alertes = []

        for ticker, infos in self.titres.items():

            prix = self.prix.get(ticker)
            ouverture = self.ouvertures.get(ticker)

            variation = None
            valeur = None

            if prix is not None and ouverture not in (None, 0):

                variation = (prix - ouverture) / ouverture * 100

                valeur = prix * infos["quantite"]

                valeur_totale += valeur

                valeur_ouverture += ouverture * infos["quantite"]

                if prix >= infos["seuil_haut"]:

                    alertes.append(
                        f"⚠️ {ticker} dépasse le seuil haut "
                        f"({prix:.2f} $ ≥ {infos['seuil_haut']:.2f} $)"
                    )

                elif prix <= infos["seuil_bas"]:

                    alertes.append(
                        f"⚠️ {ticker} sous le seuil bas "
                        f"({prix:.2f} $ ≤ {infos['seuil_bas']:.2f} $)"
                    )

            titres[ticker] = {
                "quantite": infos["quantite"],
                "seuil_bas": infos["seuil_bas"],
                "seuil_haut": infos["seuil_haut"],
                "prix": prix,
                "ouverture": ouverture,
                "variation": variation,
                "valeur": valeur,
            }

        return {
            "horodatage": self.derniere_mise_a_jour,
            "titres": titres,
            "valeur_totale": valeur_totale,
            "valeur_ouverture": valeur_ouverture,
            "variation_portfolio": valeur_totale - valeur_ouverture,
            "alertes": alertes,
        }

    @staticmethod
    def recuperer_prix(ticker):

        info = yf.Ticker(ticker).fast_info

        prix = info["last_price"]
        ouverture = info["open"]

        if prix is None or ouverture is None:
            raise ValueError(
                f"Le titre '{ticker}' n'a pas de prix disponible."
            )

        return float(prix), float(ouverture)

    def actualiser_prix(self):

        for ticker in self.titres:

            prix, ouverture = self.recuperer_prix(ticker)

            self.prix[ticker] = prix
            self.ouvertures[ticker] = ouverture

        self.derniere_mise_a_jour = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        self.notifier()

    def ajouter_titre(
        self,
        ticker,
        quantite,
        seuil_bas=None,
        seuil_haut=None
    ):

        ticker = ticker.strip().upper()

        if not ticker:
            raise ValueError("Le ticker est obligatoire.")

        if ticker in self.titres:
            raise ValueError(
                f"{ticker} est déjà dans le portfolio."
            )

        if quantite <= 0:
            raise ValueError(
                "La quantité doit être positive."
            )

        prix, ouverture = self.recuperer_prix(ticker)

        seuil_bas = prix * 0.8 if seuil_bas is None else seuil_bas
        seuil_haut = prix * 1.2 if seuil_haut is None else seuil_haut

        if (
            seuil_bas <= 0
            or seuil_haut <= 0
            or seuil_bas >= seuil_haut
        ):
            raise ValueError(
                "Le seuil bas doit être positif "
                "et inférieur au seuil haut."
            )

        self.titres[ticker] = {
            "quantite": int(quantite),
            "seuil_bas": round(float(seuil_bas), 2),
            "seuil_haut": round(float(seuil_haut), 2),
        }

        self.prix[ticker] = prix
        self.ouvertures[ticker] = ouverture

        self.derniere_mise_a_jour = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        self.notifier()

    def retirer_titre(self, ticker):

        if ticker not in self.titres:
            raise ValueError(
                f"{ticker} n'est pas dans le portfolio."
            )

        del self.titres[ticker]

        self.prix.pop(ticker, None)
        self.ouvertures.pop(ticker, None)

        self.derniere_mise_a_jour = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        self.notifier()

    def modifier_titre(
        self,
        ticker,
        quantite=None,
        seuil_bas=None,
        seuil_haut=None
    ):

        if ticker not in self.titres:
            raise ValueError(
                f"{ticker} n'est pas dans le portfolio."
            )

        if quantite is not None:

            if quantite <= 0:
                raise ValueError(
                    "La quantité doit être positive."
                )

            self.titres[ticker]["quantite"] = int(quantite)

        if seuil_bas is not None or seuil_haut is not None:

            if seuil_bas is None or seuil_haut is None:
                raise ValueError(
                    "Les deux seuils doivent être fournis ensemble."
                )

            if (
                seuil_bas <= 0
                or seuil_haut <= 0
                or seuil_bas >= seuil_haut
            ):
                raise ValueError(
                    "Le seuil bas doit être positif "
                    "et inférieur au seuil haut."
                )

            self.titres[ticker]["seuil_bas"] = round(
                float(seuil_bas), 2
            )

            self.titres[ticker]["seuil_haut"] = round(
                float(seuil_haut), 2
            )

        self.derniere_mise_a_jour = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        self.notifier()