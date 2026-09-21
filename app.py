# Portfolio Tracker : suit en temps réel (toutes les INTERVALLE_MS) le prix
# de titres boursiers via yfinance, affiche la valeur du portefeuille, déclenche
# des alertes de seuil et journalise chaque cycle dans portfolio.csv.

import wx
import yfinance as yf
from datetime import datetime


# Portefeuille initial : quantité détenue + seuils d'alerte par ticker.
# Modifié en place par l'UI (ajout/retrait/modification de titres).
TITRES = {
    "AAPL":  {"quantite": 10, "seuil_haut": 200.0, "seuil_bas": 150.0},
    "GOOGL": {"quantite": 5,  "seuil_haut": 160.0, "seuil_bas": 120.0},
    "MSFT":  {"quantite": 8,  "seuil_haut": 430.0, "seuil_bas": 380.0},
}

INTERVALLE_MS = 30000  # Fréquence de rafraîchissement des prix (30 secondes)


## --- Fonctions utilitaires --- ##
# Fonctions indépendantes de l'UI : accès réseau (yfinance), formatage et
# validation. Regroupées ici pour être réutilisées à la fois par l'ajout de
# titres et le cycle de rafraîchissement, sans dupliquer la logique.

def recuperer_prix(ticker):
    """Retourne (prix, ouverture) pour un ticker, ou lève une erreur s'il est introuvable."""
    info = yf.Ticker(ticker).fast_info
    prix = info["last_price"]
    if prix is None:
        raise ValueError(f"Le titre '{ticker}' n'existe pas.")
    return prix, info["open"]


def formater_prix(prix, ouverture):
    """Retourne le texte et la couleur à afficher pour un prix et sa variation
    par rapport à l'ouverture (vert si en hausse, rouge si en baisse)."""
    variation = (prix - ouverture) / ouverture * 100
    symbole = "▲" if variation >= 0 else "▼"
    couleur = wx.Colour(0, 140, 0) if variation >= 0 else wx.Colour(180, 0, 0)
    return f"{prix:.2f} $  {symbole} {abs(variation):.2f}%", couleur


def entier_positif(texte):
    """Convertit `texte` en entier strictement positif, ou lève ValueError."""
    valeur = int(texte)
    if valeur <= 0:
        raise ValueError
    return valeur


def flottant_positif(texte):
    """Convertit `texte` en nombre décimal strictement positif, ou lève ValueError."""
    valeur = float(texte)
    if valeur <= 0:
        raise ValueError
    return valeur


class App(wx.Frame):
    def __init__(self):
        super().__init__(None, title="Portfolio Tracker")
        self.SetMinSize((480, 600))

        # labels_prix : ticker -> StaticText affichant "prix ▲/▼ variation%"
        # panels_prix : ticker -> Panel conteneur de cette ligne, pour pouvoir
        # le détruire proprement quand un titre est retiré
        self.labels_prix = {}
        self.panels_prix = {}

        panel = wx.Panel(self)
        self.main_sizer = wx.BoxSizer(wx.VERTICAL)

        titre = wx.StaticText(panel, label="Portfolio Tracker")
        font_titre = titre.GetFont()
        font_titre.SetPointSize(16)
        font_titre.SetWeight(wx.FONTWEIGHT_BOLD)
        titre.SetFont(font_titre)
        self.main_sizer.Add(titre, 0, wx.ALL | wx.CENTER, 10)

        # Section "Prix en temps réel" : une ligne par titre du portefeuille
        box_prix = wx.StaticBox(panel, label="Prix en temps réel")
        self.sizer_prix = wx.StaticBoxSizer(box_prix, wx.VERTICAL)
        for ticker in TITRES:
            self._creer_ligne_prix(panel, ticker)
        self.main_sizer.Add(self.sizer_prix, 0, wx.EXPAND | wx.ALL, 10)

        # Section "Gérer les titres" : ajout, retrait, modification (voir plus bas)
        self._construire_gestion(panel)

        # Section "Mon portfolio" : valeur totale et variation depuis l'ouverture,
        # mises à jour à chaque cycle de rafraichir()
        box_portfolio = wx.StaticBox(panel, label="Mon portfolio")
        sizer_portfolio = wx.StaticBoxSizer(box_portfolio, wx.VERTICAL)
        self.label_valeur = wx.StaticText(panel, label="Valeur totale : calcul en cours...")
        font_valeur = self.label_valeur.GetFont()
        font_valeur.SetPointSize(11)
        font_valeur.SetWeight(wx.FONTWEIGHT_BOLD)
        self.label_valeur.SetFont(font_valeur)
        self.label_variation = wx.StaticText(panel, label="")
        sizer_portfolio.Add(self.label_valeur, 0, wx.ALL, 5)
        sizer_portfolio.Add(self.label_variation, 0, wx.ALL, 5)
        self.main_sizer.Add(sizer_portfolio, 0, wx.EXPAND | wx.ALL, 10)

        # Section "Alertes" : liste des titres ayant franchi un seuil, ou message par défaut
        box_alertes = wx.StaticBox(panel, label="Alertes")
        sizer_alertes = wx.StaticBoxSizer(box_alertes, wx.VERTICAL)
        self.label_alertes = wx.StaticText(panel, label="Aucune alerte")
        self.label_alertes.SetForegroundColour(wx.Colour(128, 128, 128))
        sizer_alertes.Add(self.label_alertes, 0, wx.ALL, 5)
        self.main_sizer.Add(sizer_alertes, 0, wx.EXPAND | wx.ALL, 10)

        self.label_maj = wx.StaticText(panel, label="")
        self.label_maj.SetForegroundColour(wx.Colour(128, 128, 128))
        self.main_sizer.Add(self.label_maj, 0, wx.ALL | wx.CENTER, 5)

        panel.SetSizer(self.main_sizer)
        self.main_sizer.Fit(self)
        self.Centre()
        self.Show()

        # Premier chargement des prix, puis boucle de rafraîchissement automatique
        # (rafraichir() se replanifie elle-même via wx.CallLater)
        self.rafraichir()

    # ---------------------------------------------------------------- UI --

    def _construire_gestion(self, panel):
        """Construit la section "Gérer les titres" : formulaire d'ajout, liste
        des titres du portefeuille (avec retrait), et formulaire de modification
        de la sélection courante."""
        box = wx.StaticBox(panel, label="Gérer les titres")
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)

        # Ligne 1 : formulaire d'ajout d'un nouveau titre
        ligne_ajout = wx.BoxSizer(wx.HORIZONTAL)
        self.entry_ticker = self._champ(panel, ligne_ajout, "Ticker", width=80)
        self.entry_quantite = self._champ(panel, ligne_ajout, "Qté", width=40, valeur_defaut="1")
        self.entry_seuil_bas_ajout = self._champ(panel, ligne_ajout, "Alerte basse", width=70)
        self.entry_seuil_haut_ajout = self._champ(panel, ligne_ajout, "Alerte haute", width=70)
        btn_ajouter = wx.Button(panel, label="Ajouter")
        btn_ajouter.Bind(wx.EVT_BUTTON, lambda e: self.ajouter_titre())
        ligne_ajout.Add(btn_ajouter, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(ligne_ajout, 0, wx.ALL, 5)

        note = wx.StaticText(panel, label="(Alertes optionnelles : si vides, calculées à ±20% du prix actuel)")
        font_note = note.GetFont()
        font_note.SetPointSize(8)
        note.SetFont(font_note)
        note.SetForegroundColour(wx.Colour(128, 128, 128))
        sizer.Add(note, 0, wx.LEFT | wx.BOTTOM, 5)

        # Ligne 2 : liste des titres actuellement dans le portefeuille + retrait
        # (la sélection dans cette liste sert aussi au formulaire de modification ci-dessous)
        ligne_liste = wx.BoxSizer(wx.HORIZONTAL)
        self.listbox_titres = wx.ListBox(panel, style=wx.LB_SINGLE)
        for ticker in TITRES:
            self.listbox_titres.Append(self._texte_listbox(ticker))
        ligne_liste.Add(self.listbox_titres, 1, wx.EXPAND | wx.RIGHT, 5)
        btn_retirer = wx.Button(panel, label="Retirer")
        btn_retirer.Bind(wx.EVT_BUTTON, lambda e: self.retirer_titre())
        ligne_liste.Add(btn_retirer, 0, wx.ALIGN_TOP)
        sizer.Add(ligne_liste, 0, wx.EXPAND | wx.ALL, 5)

        # Ligne 3 : modification de la quantité et/ou des seuils du titre sélectionné
        ligne_modif = wx.BoxSizer(wx.HORIZONTAL)
        ligne_modif.Add(wx.StaticText(panel, label="Sélection →"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.entry_nouvelle_quantite = self._champ(panel, ligne_modif, "Qté", width=40)
        self.entry_nouveau_seuil_bas = self._champ(panel, ligne_modif, "Alerte basse", width=70)
        self.entry_nouveau_seuil_haut = self._champ(panel, ligne_modif, "Alerte haute", width=70)
        btn_modifier = wx.Button(panel, label="Modifier sélection")
        btn_modifier.Bind(wx.EVT_BUTTON, lambda e: self.modifier_selection())
        ligne_modif.Add(btn_modifier, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(ligne_modif, 0, wx.ALL, 5)

        # Message de statut (succès / erreur) pour les actions de cette section
        self.label_statut_titres = wx.StaticText(panel, label="")
        self.label_statut_titres.SetForegroundColour(wx.Colour(128, 128, 128))
        sizer.Add(self.label_statut_titres, 0, wx.LEFT | wx.BOTTOM, 5)

        self.main_sizer.Add(sizer, 0, wx.EXPAND | wx.ALL, 10)
        self._panel_gestion = panel   # gardé pour _creer_ligne_prix post-init

    def _champ(self, panel, sizer, texte, width, valeur_defaut=""):
        """Ajoute un couple StaticText + TextCtrl à `sizer` et retourne le TextCtrl."""
        sizer.Add(wx.StaticText(panel, label=f"{texte}:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 3)
        ctrl = wx.TextCtrl(panel, size=(width, -1))
        if valeur_defaut:
            ctrl.SetValue(valeur_defaut)
        sizer.Add(ctrl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        return ctrl

    def _creer_ligne_prix(self, panel, ticker):
        """Ajoute la ligne d'affichage de prix pour un ticker (appelé au
        démarrage pour chaque titre, et à nouveau quand un titre est ajouté)."""
        ligne = wx.BoxSizer(wx.HORIZONTAL)
        lbl_ticker = wx.StaticText(panel, label=f"{ticker}:")
        font_bold = lbl_ticker.GetFont()
        font_bold.SetWeight(wx.FONTWEIGHT_BOLD)
        lbl_ticker.SetFont(font_bold)
        lbl_ticker.SetMinSize((70, -1))
        ligne.Add(lbl_ticker, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        label = wx.StaticText(panel, label="Chargement...")
        ligne.Add(label, 0, wx.ALIGN_CENTER_VERTICAL)
        self.labels_prix[ticker] = label
        self.panels_prix[ticker] = ligne
        self.sizer_prix.Add(ligne, 0, wx.ALL, 3)

    def _texte_listbox(self, ticker):
        """Construit la ligne texte affichée dans la liste pour un ticker."""
        infos = TITRES[ticker]
        return (
            f"{ticker} — {infos['quantite']} action(s) "
            f"(alerte : {infos['seuil_bas']:.2f} $ / {infos['seuil_haut']:.2f} $)"
        )

    def _rafraichir_ligne_listbox(self, index, ticker):
        """Remplace la ligne `index` par sa version à jour et la garde sélectionnée."""
        self.listbox_titres.Delete(index)
        self.listbox_titres.Insert(self._texte_listbox(ticker), index)
        self.listbox_titres.SetSelection(index)

    def _ticker_selectionne(self):
        """Retourne (index, ticker) du titre sélectionné dans la liste, ou None.
        Le ticker est extrait du texte affiché (avant le tiret "—")."""
        index = self.listbox_titres.GetSelection()
        if index == wx.NOT_FOUND:
            return None
        texte = self.listbox_titres.GetString(index)
        return index, texte.split(" — ")[0]

    def _statut(self, texte, couleur):
        """Affiche un message de statut (succès/erreur/info) sous le formulaire de gestion."""
        couleurs = {
            "green":  wx.Colour(0, 140, 0),
            "red":    wx.Colour(180, 0, 0),
            "orange": wx.Colour(200, 100, 0),
            "gray":   wx.Colour(128, 128, 128),
        }
        self.label_statut_titres.SetLabel(texte)
        self.label_statut_titres.SetForegroundColour(couleurs.get(couleur, wx.NullColour))

    # ----------------------------------------------------------- actions --

    def ajouter_titre(self):
        """Valide le formulaire d'ajout, vérifie que le ticker existe via yfinance,
        puis l'insère dans TITRES et dans l'UI (ligne de prix + liste)."""
        ticker = self.entry_ticker.GetValue().strip().upper()
        if not ticker:
            return
        if ticker in TITRES:
            self._statut(f"{ticker} est déjà dans le portfolio.", "orange")
            return

        try:
            quantite = entier_positif(self.entry_quantite.GetValue().strip())
        except ValueError:
            self._statut("La quantité doit être un nombre entier positif.", "red")
            return

        # Les seuils sont optionnels à l'ajout : s'ils sont vides, on les
        # calcule plus bas à ±20% du prix actuel une fois celui-ci connu.
        texte_bas = self.entry_seuil_bas_ajout.GetValue().strip()
        texte_haut = self.entry_seuil_haut_ajout.GetValue().strip()
        try:
            seuil_bas = flottant_positif(texte_bas) if texte_bas else None
            seuil_haut = flottant_positif(texte_haut) if texte_haut else None
        except ValueError:
            self._statut("Les alertes doivent être des nombres positifs.", "red")
            return
        if seuil_bas is not None and seuil_haut is not None and seuil_bas >= seuil_haut:
            self._statut("L'alerte basse doit être inférieure à l'alerte haute.", "red")
            return

        # Le ticker n'existe vraiment que si yfinance renvoie un prix
        try:
            prix, ouverture = recuperer_prix(ticker)
        except Exception:
            self._statut(f"Le titre '{ticker}' n'existe pas.", "red")
            return

        TITRES[ticker] = {
            "quantite": quantite,
            "seuil_haut": round(seuil_haut if seuil_haut is not None else prix * 1.2, 2),
            "seuil_bas":  round(seuil_bas  if seuil_bas  is not None else prix * 0.8, 2),
        }

        # Mise à jour de l'UI : nouvelle ligne de prix, nouvelle entrée dans la
        # liste, puis réinitialisation du formulaire d'ajout
        self._creer_ligne_prix(self._panel_gestion, ticker)
        self.sizer_prix.GetStaticBox().GetParent().Layout()
        self.listbox_titres.Append(self._texte_listbox(ticker))
        self.entry_ticker.Clear()
        self.entry_quantite.SetValue("1")
        self.entry_seuil_bas_ajout.Clear()
        self.entry_seuil_haut_ajout.Clear()

        # Affiche le prix tout de suite plutôt que d'attendre le prochain
        # cycle de rafraichir() (jusqu'à INTERVALLE_MS plus tard)
        texte, couleur = formater_prix(prix, ouverture)
        self.labels_prix[ticker].SetLabel(texte)
        self.labels_prix[ticker].SetForegroundColour(couleur)
        self._statut(f"{ticker} ajouté au portfolio ({quantite} action(s)).", "green")

    def retirer_titre(self):
        """Retire le titre sélectionné dans la liste : du portefeuille (TITRES),
        de la liste, et détruit sa ligne de prix."""
        selectionne = self._ticker_selectionne()
        if selectionne is None:
            self._statut("Sélectionnez un titre à retirer.", "orange")
            return
        index, ticker = selectionne

        self.listbox_titres.Delete(index)
        del TITRES[ticker]
        self.labels_prix.pop(ticker, None)
        ligne = self.panels_prix.pop(ticker)
        # Détruire les widgets de la ligne avant de retirer le sizer
        for item in reversed(range(ligne.GetItemCount())):
            widget = ligne.GetItem(item).GetWindow()
            if widget:
                widget.Destroy()
        self.sizer_prix.Remove(ligne)
        self.sizer_prix.GetStaticBox().GetParent().Layout()
        self.Fit()

        self._statut(f"{ticker} retiré du portfolio.", "gray")

    def modifier_selection(self):
        """Met à jour la quantité et/ou les seuils d'alerte du titre sélectionné.
        Chaque champ est optionnel : seuls ceux remplis sont modifiés, mais les
        deux seuils doivent être fournis ensemble pour rester cohérents."""
        selectionne = self._ticker_selectionne()
        if selectionne is None:
            self._statut("Sélectionnez un titre à modifier.", "orange")
            return
        index, ticker = selectionne

        texte_qte = self.entry_nouvelle_quantite.GetValue().strip()
        texte_bas = self.entry_nouveau_seuil_bas.GetValue().strip()
        texte_haut = self.entry_nouveau_seuil_haut.GetValue().strip()
        if not texte_qte and not texte_bas and not texte_haut:
            self._statut("Entrez une nouvelle quantité et/ou de nouvelles alertes.", "orange")
            return

        changements = []
        try:
            if texte_qte:
                TITRES[ticker]["quantite"] = entier_positif(texte_qte)
                changements.append(f"{TITRES[ticker]['quantite']} action(s)")
            if texte_bas or texte_haut:
                if not (texte_bas and texte_haut):
                    self._statut("Les deux alertes doivent être fournies ensemble.", "red")
                    return
                seuil_bas, seuil_haut = flottant_positif(texte_bas), flottant_positif(texte_haut)
                if seuil_bas >= seuil_haut:
                    self._statut("L'alerte basse doit être inférieure à l'alerte haute.", "red")
                    return
                TITRES[ticker]["seuil_bas"] = round(seuil_bas, 2)
                TITRES[ticker]["seuil_haut"] = round(seuil_haut, 2)
                changements.append(f"alertes {seuil_bas:.2f} $ / {seuil_haut:.2f} $")
        except ValueError:
            self._statut("La quantité et les alertes doivent être des nombres positifs.", "red")
            return

        self._rafraichir_ligne_listbox(index, ticker)
        self.entry_nouvelle_quantite.Clear()
        self.entry_nouveau_seuil_bas.Clear()
        self.entry_nouveau_seuil_haut.Clear()
        self._statut(f"{ticker} mis à jour : {', '.join(changements)}.", "green")

    # ------------------------------------------------------------ cycle --

    def rafraichir(self):
        """Cycle principal : récupère les prix de tous les titres, met à jour
        l'affichage (prix, valeur totale, alertes), journalise dans le CSV,
        puis se replanifie elle-même dans INTERVALLE_MS millisecondes.
        Toute erreur (ex. réseau) est affichée sans interrompre le cycle."""
        try:
            # 1. Récupération des prix actuels pour tous les titres du portefeuille
            prix_actuels = {ticker: recuperer_prix(ticker) for ticker in TITRES}

            # 2. Mise à jour de l'affichage prix/variation de chaque titre
            for ticker, (prix, ouverture) in prix_actuels.items():
                texte, couleur = formater_prix(prix, ouverture)
                self.labels_prix[ticker].SetLabel(texte)
                self.labels_prix[ticker].SetForegroundColour(couleur)

            # 3. Valeur totale du portefeuille et variation depuis l'ouverture
            valeur_totale = sum(prix * TITRES[t]["quantite"] for t, (prix, _) in prix_actuels.items())
            valeur_ouverture = sum(ouv * TITRES[t]["quantite"] for t, (_, ouv) in prix_actuels.items())
            variation_portfolio = valeur_totale - valeur_ouverture

            self.label_valeur.SetLabel(f"Valeur totale : {valeur_totale:.2f} $")
            symbole = "▲" if variation_portfolio >= 0 else "▼"
            self.label_variation.SetLabel(
                f"{symbole} {abs(variation_portfolio):.2f} $ depuis l'ouverture"
            )
            couleur_var = wx.Colour(0, 140, 0) if variation_portfolio >= 0 else wx.Colour(180, 0, 0)
            self.label_variation.SetForegroundColour(couleur_var)

            # 4. Alertes : un titre est signalé s'il atteint ou dépasse son seuil haut,
            # ou atteint ou descend sous son seuil bas
            alertes = []
            for ticker, (prix, _) in prix_actuels.items():
                if prix >= TITRES[ticker]["seuil_haut"]:
                    alertes.append(f"⚠️ {ticker} dépasse le seuil haut ({prix:.2f} $ ≥ {TITRES[ticker]['seuil_haut']:.2f} $)")
                elif prix <= TITRES[ticker]["seuil_bas"]:
                    alertes.append(f"⚠️ {ticker} sous le seuil bas ({prix:.2f} $ ≤ {TITRES[ticker]['seuil_bas']:.2f} $)")
            self.label_alertes.SetLabel("\n".join(alertes) if alertes else "Aucune alerte")
            self.label_alertes.SetForegroundColour(
                wx.Colour(180, 0, 0) if alertes else wx.Colour(128, 128, 128)
            )

            # 5. Journalisation : une ligne par titre est ajoutée au CSV à chaque cycle
            horodatage = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open("portfolio.csv", "a") as f:
                for ticker, (prix, ouverture) in prix_actuels.items():
                    f.write(f"{horodatage},{ticker},{prix:.2f},{ouverture:.2f}\n")

            self.label_maj.SetLabel(f"Dernière mise à jour : {horodatage}")
            self.label_maj.SetForegroundColour(wx.Colour(128, 128, 128))

        except Exception as e:
            self.label_maj.SetLabel(f"Erreur : {e}")
            self.label_maj.SetForegroundColour(wx.Colour(180, 0, 0))

        # Replanifie le prochain cycle, que celui-ci ait réussi ou échoué
        wx.CallLater(INTERVALLE_MS, self.rafraichir)


if __name__ == "__main__":
    app = wx.App()
    App()
    app.MainLoop()