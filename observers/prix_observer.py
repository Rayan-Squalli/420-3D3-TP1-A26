from observers.observer import Observateur


class PrixObserver(Observateur):

    def actualiser(self, sujet) -> None:

        donnees = sujet.get_donnees()

        print("\n=== PRIX DES TITRES ===")

        for ticker, infos in donnees["titres"].items():

            prix = infos["prix"]
            variation = infos["variation"]

            if prix is None:
                print(f"{ticker}: prix indisponible")
                continue

            if variation is None:
                print(f"{ticker}: {prix:.2f} $")
            else:
                print(
                    f"{ticker}: {prix:.2f} $ "
                    f"({variation:+.2f} %)"
                )