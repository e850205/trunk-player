import re
from django import forms
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from django_select2.forms import (
    HeavySelect2MultipleWidget, HeavySelect2Widget, ModelSelect2MultipleWidget,
    ModelSelect2TagWidget, ModelSelect2Widget, Select2MultipleWidget,
    Select2Widget
)

from .models import Unit, Profile, TalkGroup, ScanList


class UserScanForm(forms.Form):
    name = forms.CharField(max_length=30)
    talkgroups = forms.ModelMultipleChoiceField(
        widget=ModelSelect2MultipleWidget(
            queryset=TalkGroup.objects.all(),
            search_fields=['alpha_tag__icontains', 'common_name__icontains'],
        ), queryset=TalkGroup.objects.all(), required=True)

    def __init__(self, *args, talkgroups=None, **kwargs):
        super().__init__(*args, **kwargs)
        if talkgroups is not None:
            # Only offer (and accept) talkgroups the user can see
            self.fields['talkgroups'].queryset = talkgroups
            self.fields['talkgroups'].widget.queryset = talkgroups

    def clean_name(self):
        data = self.cleaned_data['name']
        if ScanList.objects.filter(name=data).exists() or ScanList.objects.filter(slug=slugify(data)).exists():
            raise forms.ValidationError("Scan list with same name already exists")
        if not slugify(data):
            raise forms.ValidationError("Use some letters or numbers in the name")

        # Always return a value to use as the new cleaned data, even if
        # this method didn't change it.
        return data


class UnitEditForm(forms.ModelForm):

    class Meta:
        model = Unit
        fields = ['description',]


class UserForm(forms.ModelForm):
    username = forms.CharField(
                       widget=forms.TextInput(attrs={'readonly':'readonly'})
               )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
