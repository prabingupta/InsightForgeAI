from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DetailView, ListView

from apps.accounts.models import User
from apps.organizations.forms import InviteMemberForm, OrganizationForm
from apps.organizations.models import Membership, Organization
from apps.organizations.permissions import get_membership, require_role


class OrganizationListView(LoginRequiredMixin, ListView):
    model = Organization
    template_name = 'organizations/list.html'
    context_object_name = 'organizations'

    def get_queryset(self):
        return Organization.objects.filter(memberships__user=self.request.user)


class OrganizationCreateView(LoginRequiredMixin, CreateView):
    model = Organization
    form_class = OrganizationForm
    template_name = 'organizations/create.html'
    success_url = reverse_lazy('organizations:list')

    def form_valid(self, form):
        form.instance.owner = self.request.user
        response = super().form_valid(form)
        Membership.objects.create(
            user=self.request.user,
            organization=self.object,
            role=Membership.Role.OWNER,
        )
        messages.success(self.request, f'Organization "{self.object.name}" created.')
        return response


class OrganizationDetailView(LoginRequiredMixin, DetailView):
    model = Organization
    template_name = 'organizations/detail.html'
    context_object_name = 'organization'
    slug_url_kwarg = 'slug'

    def get_object(self, queryset=None):
        organization = get_object_or_404(Organization, slug=self.kwargs['slug'])
        membership = get_membership(self.request.user, organization)
        if membership is None:
            raise PermissionDenied('You do not have access to this organization.')
        self.membership = membership
        return organization

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['membership'] = self.membership
        context['members'] = Membership.objects.filter(
            organization=self.object
        ).select_related('user')
        context['invite_form'] = InviteMemberForm()
        return context


class InviteMemberView(LoginRequiredMixin, CreateView):
    form_class = InviteMemberForm
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        organization = get_object_or_404(Organization, slug=self.kwargs['slug'])
        require_role(request.user, organization, [Membership.Role.OWNER, Membership.Role.ADMIN])

        form = InviteMemberForm(request.POST)
        if form.is_valid():
            try:
                target_user = User.objects.get(username=form.cleaned_data['username'])
            except User.DoesNotExist:
                messages.error(request, 'No user found with that username.')
                return redirect('organizations:detail', slug=organization.slug)

            if Membership.objects.filter(user=target_user, organization=organization).exists():
                messages.error(request, f'{target_user.username} is already a member.')
            else:
                Membership.objects.create(
                    user=target_user,
                    organization=organization,
                    role=form.cleaned_data['role'],
                )
                messages.success(request, f'{target_user.username} added to {organization.name}.')
        else:
            messages.error(request, 'Invalid invite request.')

        return redirect('organizations:detail', slug=organization.slug)
