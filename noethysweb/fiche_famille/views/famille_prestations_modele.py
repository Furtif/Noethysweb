# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from dateutil import rrule
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from django.views.generic import TemplateView
from core.views import crud
from core.models import Prestation
from fiche_famille.forms.famille_prestations_modele import Formulaire, Formulaire_selection_modele
from fiche_famille.views.famille import Onglet


class Page(Onglet):
    model = Prestation
    description_saisie = "Saisissez toutes les informations concernant la prestation et cliquez sur le bouton Enregistrer."
    objet_singulier = "une prestation"
    objet_pluriel = "des prestations"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        context['onglet_actif'] = "prestations"
        return context

    def get_form_kwargs(self, **kwargs):
        """ Envoie l'idindividu au formulaire """
        form_kwargs = super(Page, self).get_form_kwargs(**kwargs)
        form_kwargs["idfamille"] = self.Get_idfamille()
        form_kwargs["idmodele"] = self.kwargs.get("idmodele", None)
        return form_kwargs

    def get_success_url(self):
        """ Renvoie vers la liste après le formulaire """
        return reverse_lazy("famille_prestations_liste", kwargs={'idfamille': self.kwargs.get('idfamille', None)})


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire
    template_name = "fiche_famille/famille_edit.html"

    def form_valid(self, form):
        # Enregistrement de la prestation unique
        if not form.cleaned_data["multiprestations"]:
            prestation = form.save(commit=True)

        # Si REPARTITION_MENSUELLE
        if form.cleaned_data["multiprestations"] in ("REPARTITION_MENSUELLE_X_MOIS", "REPARTITION_MENSUELLE_DATES"):
            nbre_mensualites = form.cleaned_data["nbre_mois"]
            if form.cleaned_data["multiprestations"] == "REPARTITION_MENSUELLE_X_MOIS":
                liste_dates = list(rrule.rrule(rrule.MONTHLY, dtstart=form.cleaned_data["date"], count=nbre_mensualites))
            else:
                liste_dates = self.Get_selection_dates(form.cleaned_data["selection_dates"])
            mensualite = form.cleaned_data["montant"] // nbre_mensualites
            for index, date in enumerate(liste_dates, start=1):
                # Préparation des valeurs de la prestation
                valeurs = self.Get_valeurs_prestation(form)
                valeurs["date"] = date
                valeurs["montant"] = mensualite
                # Ajout du modulo à la dernière mensualité
                if index == nbre_mensualites:
                    valeurs["montant"] += form.cleaned_data["montant"] % nbre_mensualites
                # Enregistrement de la prestation
                Prestation.objects.create(**valeurs)

        # Si MULTIPLICATION_MENSUELLE
        if form.cleaned_data["multiprestations"] in ("MULTIPLICATION_MENSUELLE_X_MOIS", "MULTIPLICATION_MENSUELLE_DATES"):
            if form.cleaned_data["multiprestations"] == "MULTIPLICATION_MENSUELLE_X_MOIS":
                liste_dates = list(rrule.rrule(rrule.MONTHLY, dtstart=form.cleaned_data["date"], count=form.cleaned_data["nbre_mois"]))
            else:
                liste_dates = self.Get_selection_dates(form.cleaned_data["selection_dates"])
            for index, date in enumerate(liste_dates, start=1):
                valeurs = self.Get_valeurs_prestation(form)
                valeurs["date"] = date
                Prestation.objects.create(**valeurs)

        return HttpResponseRedirect(self.get_success_url())

    def Get_valeurs_prestation(self, form=None):
        return {key: valeur for key, valeur in form.cleaned_data.items() if key not in ("multiprestations", "nbre_mois", "selection_dates")}

    def Get_selection_dates(self, selection_dates=""):
        liste_dates = []
        for date in selection_dates.split(";"):
            liste_dates.append(datetime.datetime.strptime(date.strip(), "%d/%m/%Y").date())
        return liste_dates


class Selection_modele(Onglet, TemplateView):
    template_name = "fiche_famille/famille_edit.html"

    def get_context_data(self, **kwargs):
        context = super(Selection_modele, self).get_context_data(**kwargs)
        if not hasattr(self, "verbe_action"):
            context['box_titre'] = "Sélection d'un modèle de prestation"
        context['box_introduction'] = "Vous devez commencer par sélectionner le modèle de prestation à appliquer. Les modèles peuvent être créés depuis le menu Paramétrage."
        context['onglet_actif'] = "prestations"
        context['form'] = Formulaire_selection_modele(request=self.request)
        return context

    def post(self, request, **kwargs):
        idmodele = int(request.POST.get("modele"))
        return HttpResponseRedirect(reverse_lazy("famille_prestations_ajouter_modele", args=(self.Get_idfamille(), idmodele)))

    def Get_annuler_url(self):
        return reverse_lazy("famille_prestations_liste", kwargs={'idfamille': self.kwargs.get('idfamille', None)})
