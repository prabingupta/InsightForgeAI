from django import forms

from apps.organizations.models import Membership, Organization


class OrganizationForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = ('name',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})


class InviteMemberForm(forms.Form):
    username = forms.CharField(max_length=150)
    role = forms.ChoiceField(choices=Membership.Role.choices)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
