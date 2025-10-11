from django.core.management.base import BaseCommand
from elections.models import Election
from django.utils import timezone


class Command(BaseCommand):
    help = 'Check and update election statuses based on current time'

    def handle(self, *args, **options):
        # Get all elections
        elections = Election._default_manager.all()
        
        updated_count = 0
        for election in elections:
            old_status = election.status
            election.check_and_update_status()
            if election.status != old_status:
                updated_count += 1
                self.stdout.write(
                    f'Updated election "{election.title}" from {old_status} to {election.status}'
                )
        
        self.stdout.write(
            f'Successfully checked {elections.count()} elections, updated {updated_count} elections'
        )