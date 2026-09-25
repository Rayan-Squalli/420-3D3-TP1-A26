from observers.observer import Observateur


class PortfolioObserver(Observateur):

    def actualiser(self, sujet) -> None:

        donnees = sujet.get_donnees()

        valeur = donnees["valeur_totale"]
        variation = donnees["variation_portfolio"]

        print("\n=== PORTFOLIO ===")

        print(
            f"Valeur totale : {valeur:.2f} $"
        )

        print(
            f"Variation : {variation:+.2f} $"
        )