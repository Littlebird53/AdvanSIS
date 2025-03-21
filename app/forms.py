from django import forms
from app import models
from django.utils.translation import gettext_lazy as _

class ContactUpdateForm(forms.ModelForm):
    class Meta:
        model = models.Person
        fields = ['given_name', 'middle_name', 'family_name',
                  'title', 'suffix', 'preferred_name', 'date_of_birth',
                  'sex', 'marital_status', 'denomination']
