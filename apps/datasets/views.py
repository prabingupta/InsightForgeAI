from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import CreateView, DetailView, ListView

from apps.datasets.forms import DatasetUploadForm
from apps.datasets.models import Dataset
from apps.datasets.processing import process_dataset
from apps.organizations.models import Membership, Organization
from apps.organizations.permissions import get_membership, require_role


class DatasetListView(LoginRequiredMixin, ListView):
    template_name = 'datasets/list.html'
    context_object_name = 'datasets'

    def get_organization(self) -> Organization:
        organization = get_object_or_404(Organization, slug=self.kwargs['org_slug'])
        self.membership = get_membership(self.request.user, organization)
        if self.membership is None:
            raise PermissionDenied('You do not have access to this organization.')
        return organization

    def get_queryset(self):
        self.organization = self.get_organization()
        return Dataset.objects.filter(organization=self.organization).select_related('owner')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['organization'] = self.organization
        context['membership'] = self.membership
        return context


class DatasetUploadView(LoginRequiredMixin, CreateView):
    form_class = DatasetUploadForm
    template_name = 'datasets/upload.html'

    def dispatch(self, request, *args, **kwargs):
        self.organization = get_object_or_404(Organization, slug=self.kwargs['org_slug'])
        require_role(
            request.user,
            self.organization,
            [Membership.Role.OWNER, Membership.Role.ADMIN, Membership.Role.ANALYST],
        )
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.organization = self.organization
        form.instance.owner = self.request.user
        uploaded_file = form.cleaned_data['file']
        form.instance.original_filename = uploaded_file.name
        form.instance.file_size = uploaded_file.size
        response = super().form_valid(form)
        process_dataset(self.object)
        messages.success(self.request, f'Dataset "{self.object.name}" uploaded successfully.')
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['organization'] = self.organization
        return context

    def get_success_url(self):
        return reverse('datasets:detail', kwargs={
            'org_slug': self.organization.slug,
            'pk': self.object.pk,
        })


class DatasetDetailView(LoginRequiredMixin, DetailView):
    model = Dataset
    template_name = 'datasets/detail.html'
    context_object_name = 'dataset'

    def get_object(self, queryset=None):
        organization = get_object_or_404(Organization, slug=self.kwargs['org_slug'])
        membership = get_membership(self.request.user, organization)
        if membership is None:
            raise PermissionDenied('You do not have access to this organization.')
        self.membership = membership
        self.organization = organization
        return get_object_or_404(Dataset, pk=self.kwargs['pk'], organization=organization)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['organization'] = self.organization
        context['membership'] = self.membership
        return context
