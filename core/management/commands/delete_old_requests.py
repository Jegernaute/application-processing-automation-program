from django.core.management.base import BaseCommand
from core.models import Request
from django.utils import timezone
from datetime import timedelta

class Command(BaseCommand):
    help = 'Видаляє заявки зі статусом done, які старші за 30 днів'

    def handle(self, *args, **kwargs):
        threshold_date = timezone.now() - timedelta(days=30)
        old_requests = Request.objects.filter(status='done',  completed_at__lt=threshold_date)

        count = old_requests.count()
        old_requests.delete()

        self.stdout.write(self.style.SUCCESS(
            f'Видалено {count} заявок зі статусом "done", старших за 30 днів.'
        ))
