from django.urls import path

from apps.datasets import views

app_name = 'datasets'

urlpatterns = [
    path('<slug:org_slug>/datasets/', views.DatasetListView.as_view(), name='list'),
    path('<slug:org_slug>/datasets/upload/', views.DatasetUploadView.as_view(), name='upload'),
    path('<slug:org_slug>/datasets/<int:pk>/', views.DatasetDetailView.as_view(), name='detail'),
]
