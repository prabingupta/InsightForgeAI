from django import forms

from apps.datasets.models import Dataset
from apps.datasets.validators import validate_dataset_file


class DatasetUploadForm(forms.ModelForm):
    file = forms.FileField(validators=[validate_dataset_file])

    class Meta:
        model = Dataset
        fields = ('name', 'description', 'file')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
