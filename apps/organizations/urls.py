from django.urls import path

from apps.organizations import views

app_name = 'organizations'

urlpatterns = [
    path('', views.OrganizationListView.as_view(), name='list'),
    path('create/', views.OrganizationCreateView.as_view(), name='create'),
    path('<slug:slug>/', views.OrganizationDetailView.as_view(), name='detail'),
    path('<slug:slug>/invite/', views.InviteMemberView.as_view(), name='invite'),
]
