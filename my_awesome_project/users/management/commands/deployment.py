import os
import sys
from time import sleep

import requests
from django.core.management import BaseCommand, call_command
from django.db.migrations.recorder import MigrationRecorder


class Command(BaseCommand):
    help = (
        "Runs the deployment in our CI/CD pipeline such that a call to perform a "
        "one-time task per-deployment is not run on every single server."
    )

    @property
    def auth_token(self):
        return os.environ["CI_CD_DEPLOYMENT_AUTH_TOKEN"]

    def run_migration(self, last_migration):
        # TODO Change this domain!!! Remember, you can't use the site model!
        r = requests.post(
            "https://donate-anything.org/", headers={"Authorization": self.auth_token}
        )
        if not r.ok:
            self.stdout.write(self.style.ERROR("Failed to migrate!"))
            sys.exit(1)
        data = r.json()
        if data["name"] == last_migration.name and data["app"] == last_migration.app:
            self.stdout.write(self.style.SUCCESS("Successfully migrated tables"))
            return
        # Re-run until we get our migration
        sleep(1)
        return self.run_migration(last_migration)

    def handle_command(self, *args, **options):
        call_command("migrate", interactive=False)
        last_migration = MigrationRecorder.Migration.objects.latest("id")
        self.run_migration(last_migration)
