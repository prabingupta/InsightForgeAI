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
    INVITABLE_ROLES = [
        choice for choice in Membership.Role.choices
        if choice[0] != Membership.Role.OWNER
    ]

    role = forms.ChoiceField(choices=INVITABLE_ROLES)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
