from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.management import call_command
from django.db.migrations.recorder import MigrationRecorder
from django.http import HttpResponse, JsonResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, RedirectView, UpdateView

User = get_user_model()


@csrf_exempt
@require_POST
def migrate(request):
    """
    User does not need to be authenticated, but they need to have an authorization token
    """
    authorization_token = request.headers.get("Authorization")
    if authorization_token != settings.SINGLE_CD_AUTHORIZATION_TOKEN:
        return HttpResponse(status=403)
    # Run all commands that should only be run once per deployment
    call_command("migrate", interactive=False)
    last_migration = MigrationRecorder.Migration.objects.latest("id")
    return JsonResponse({"app": last_migration.app, "name": last_migration.name})


class UserDetailView(LoginRequiredMixin, DetailView):

    model = User
    slug_field = "username"
    slug_url_kwarg = "username"


user_detail_view = UserDetailView.as_view()


class UserUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):

    model = User
    fields = ["name"]
    success_message = _("Information successfully updated")

    def get_success_url(self):
        return self.request.user.get_absolute_url()  # type: ignore [union-attr]

    def get_object(self):
        return self.request.user


user_update_view = UserUpdateView.as_view()


class UserRedirectView(LoginRequiredMixin, RedirectView):

    permanent = False

    def get_redirect_url(self):
        return reverse("users:detail", kwargs={"username": self.request.user.username})


user_redirect_view = UserRedirectView.as_view()
