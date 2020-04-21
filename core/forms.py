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


class PadForm(forms.Form):
    """The form to edit the pad."""

    pad_field = forms.CharField(
        label="pad_label", widget=forms.Textarea, required=False
    )

    # everytime a new form is generated, it should look up the content from the database
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super(PadForm, self).__init__(*args, **kwargs)
        # now we can add fields using a dictionary!
        self.initial["pad_field"] = Pad.objects.all()[0].content


class MusiqForm(forms.Form):
    """The form to submit new music."""

    submit_musiq = forms.CharField(label="musiq_form_label", max_length=200)
