from abc import ABC, abstractmethod


class Sujet(ABC):

    def __init__(self):
        self._observateurs = []

    def abonner(self, observateur) -> None:
        self._observateurs.append(observateur)

    def desabonner(self, observateur) -> None:
        if observateur in self._observateurs:
            self._observateurs.remove(observateur)

    def notifier(self) -> None:
        for observateur in self._observateurs:
            observateur.actualiser(self)

    @abstractmethod
    def get_donnees(self) -> dict:
        pass