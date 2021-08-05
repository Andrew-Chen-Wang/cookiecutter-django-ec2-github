from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class UsersConfig(AppConfig):
    name = "my_awesome_project.users"
    verbose_name = _("Users")

    def ready(self):
        try:
            import my_awesome_project.users.signals  # noqa F401
        except ImportError:
            pass
