import tkinter as tk
from tkinter import messagebox, ttk

from models.portfolio import PortfolioSujet
from observers.alerte_observer import AlerteObserver
from observers.csv_observer import CSVObserver
from observers.portfolio_observer import PortfolioObserver
from observers.prix_observer import PrixObserver


class Application(tk.Tk):

    def __init__(self):

        super().__init__()

        self.title("Suiveur de portefeuille boursier")
        self.geometry("900x600")

        self.portfolio = PortfolioSujet()

        self.prix_observer = PrixObserver()
        self.portfolio_observer = PortfolioObserver()
        self.alerte_observer = AlerteObserver()
        self.csv_observer = CSVObserver()

        self.portfolio.abonner(self.prix_observer)
        self.portfolio.abonner(self.portfolio_observer)
        self.portfolio.abonner(self.alerte_observer)
        self.portfolio.abonner(self.csv_observer)

        self.creer_interface()

    def creer_interface(self):

        titre = tk.Label(
            self,
            text="Suiveur de portefeuille boursier",
            font=("Arial", 20)
        )

        titre.pack(pady=15)

        self.tableau = ttk.Treeview(
            self,
            columns=(
                "ticker",
                "quantite",
                "prix",
                "variation",
                "valeur"
            ),
            show="headings"
        )

        self.tableau.heading("ticker", text="Titre")
        self.tableau.heading("quantite", text="Quantité")
        self.tableau.heading("prix", text="Prix")
        self.tableau.heading("variation", text="Variation")
        self.tableau.heading("valeur", text="Valeur")

        self.tableau.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=10
        )

        bouton = tk.Button(
            self,
            text="Actualiser les prix",
            command=self.actualiser
        )

        bouton.pack(pady=10)

        self.valeur_label = tk.Label(
            self,
            text="Valeur totale : 0.00 $",
            font=("Arial", 14)
        )

        self.valeur_label.pack()

        self.actualiser()

    def actualiser(self):

        try:

            self.portfolio.actualiser_prix()

            donnees = self.portfolio.get_donnees()

            for item in self.tableau.get_children():
                self.tableau.delete(item)

            for ticker, infos in donnees["titres"].items():

                prix = infos["prix"]

                variation = infos["variation"]

                valeur = infos["valeur"]

                self.tableau.insert(
                    "",
                    "end",
                    values=(
                        ticker,
                        infos["quantite"],
                        f"{prix:.2f}" if prix is not None else "-",
                        (
                            f"{variation:+.2f} %"
                            if variation is not None
                            else "-"
                        ),
                        (
                            f"{valeur:.2f} $"
                            if valeur is not None
                            else "-"
                        )
                    )
                )

            self.valeur_label.config(
                text=(
                    f"Valeur totale : "
                    f"{donnees['valeur_totale']:.2f} $"
                )
            )

        except Exception as erreur:

            messagebox.showerror(
                "Erreur",
                str(erreur)
            )