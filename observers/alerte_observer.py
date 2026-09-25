from observers.observer import Observateur


class AlerteObserver(Observateur):

    def actualiser(self, sujet) -> None:

        donnees = sujet.get_donnees()

        alertes = donnees["alertes"]

        if not alertes:
            print("\n=== ALERTES ===")
            print("Aucune alerte.")
            return

        print("\n=== ALERTES ===")

        for alerte in alertes:
            print(alerte)