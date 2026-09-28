import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView

from apps.analytics.kpi_engine import compute_kpis
from apps.datasets.models import Dataset
from apps.datasets.processing import read_dataset_dataframe
from apps.organizations.models import Organization
from apps.organizations.permissions import get_membership

logger = logging.getLogger(__name__)


class DatasetAnalyticsView(LoginRequiredMixin, TemplateView):
    template_name = 'analytics/dataset_analytics.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization = get_object_or_404(Organization, slug=self.kwargs['org_slug'])
        if get_membership(self.request.user, organization) is None:
            raise PermissionDenied('You do not have access to this organization.')

        dataset = get_object_or_404(Dataset, pk=self.kwargs['pk'], organization=organization)
        context['organization'] = organization
        context['dataset'] = dataset
        context['kpis'] = []
        context['error'] = ''

        if dataset.processing_status != Dataset.ProcessingStatus.COMPLETED:
            context['error'] = 'Analytics are unavailable because this dataset has not been processed successfully.'
            return context

        try:
            dataframe = read_dataset_dataframe(dataset)
            context['kpis'] = compute_kpis(dataframe)
        except Exception:
            logger.exception('KPI computation failed for dataset %s', dataset.pk)
            context['error'] = 'Analytics could not be generated for this dataset.'

        return context
