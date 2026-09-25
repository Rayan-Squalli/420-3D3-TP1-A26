# Diagramme UML - Patron Observer

```mermaid
classDiagram

    class Sujet {
        <<abstract>>
        -_observateurs
        +abonner(observateur)
        +desabonner(observateur)
        +notifier()
        +get_donnees() dict
    }

    class PortfolioSujet {
        -titres
        -prix
        -ouvertures
        -derniere_mise_a_jour
        +get_donnees() dict
        +actualiser_prix()
        +ajouter_titre()
        +retirer_titre()
        +modifier_titre()
    }

    class Observateur {
        <<abstract>>
        +actualiser(sujet)
    }

    class PrixObserver {
        +actualiser(sujet)
    }

    class PortfolioObserver {
        +actualiser(sujet)
    }

    class AlerteObserver {
        +actualiser(sujet)
    }

    class CSVObserver {
        -fichier
        +actualiser(sujet)
    }

    Sujet <|-- PortfolioSujet

    Observateur <|-- PrixObserver
    Observateur <|-- PortfolioObserver
    Observateur <|-- AlerteObserver
    Observateur <|-- CSVObserver

    Sujet o-- Observateur