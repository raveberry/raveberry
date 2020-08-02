"""Contains the forms used across all pages."""
from typing import Any

from django import forms
from core.models import Pad


class TagForm(forms.Form):
    """The form for pushing hashtags."""

    submit_tag = forms.CharField(
        label="tag_form_label",
        max_length=100,
        widget=forms.TextInput(attrs={"placeholder": "Push Hashtag"}),
    )


class MusiqForm(forms.Form):
    """The form to submit new music."""

    submit_musiq = forms.CharField(label="musiq_form_label", max_length=200)
