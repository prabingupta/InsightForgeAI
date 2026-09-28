from django.urls import path

from apps.analytics import views

app_name = 'analytics'

urlpatterns = [
    path(
        '<slug:org_slug>/datasets/<int:pk>/analytics/',
        views.DatasetAnalyticsView.as_view(),
        name='dataset_analytics',
    ),
]
