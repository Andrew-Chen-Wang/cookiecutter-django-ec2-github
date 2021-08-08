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

    def make_request(self, path):
        # TODO Change this domain!!! Remember, you can't use the site model!
        try:
            return requests.post(
                f"https://donate-anything.org/{path}",
                headers={"Authorization": self.auth_token},
            )
        except requests.exceptions.ConnectionError:
            sleep(1)
            return self.make_request(path)

    def run_migration(self, last_migration):
        r = self.make_request("migrate/")
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

    def run_collectstatic(self):
        r = self.make_request("collectstatic/")
        if not r.ok:
            self.stdout.write(self.style.ERROR("Failed to collectstatic!"))
        return

    def handle(self, *args, **options):
        # Run collectstatic
        self.run_collectstatic()
        # Prep for migrate
        call_command("migrate", interactive=False)
        last_migration = MigrationRecorder.Migration.objects.latest("id")
        self.run_migration(last_migration)
