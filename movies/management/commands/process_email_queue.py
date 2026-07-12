import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from movies.models import EmailTask
from movies.email_tasks import process_pending_email_tasks, get_email_task_stats

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Process pending email tasks from the queue with retry logic and monitoring'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=20,
            help='Maximum number of email tasks to process (default: 20)',
        )
        parser.add_argument(
            '--stats',
            action='store_true',
            help='Display email queue statistics and exit',
        )
        parser.add_argument(
            '--cleanup',
            type=int,
            default=0,
            help='Delete sent emails older than X days (0 = no cleanup)',
        )

    def handle(self, *args, **options):
        if options['stats']:
            self.display_stats()
            return

        limit = options['limit']
        self.stdout.write(
            self.style.SUCCESS(
                f'Processing email queue (limit: {limit} tasks)...'
            )
        )

        try:
            processed = process_pending_email_tasks(limit=limit)
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ Successfully processed {processed} email task(s)'
                )
            )

            # Display current statistics
            self.display_stats()

            # Optional cleanup
            if options['cleanup'] > 0:
                self.cleanup_old_emails(options['cleanup'])

        except Exception as exc:
            self.stdout.write(
                self.style.ERROR(f'✗ Error processing email queue: {str(exc)}')
            )
            logger.exception('Error in process_email_queue management command')
            raise

    def display_stats(self):
        """Display email queue statistics"""
        stats = get_email_task_stats()
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('EMAIL QUEUE STATISTICS'))
        self.stdout.write('='*60)

        for status, count in stats.items():
            if status == 'Failed':
                style = self.style.ERROR
            elif status == 'Sent':
                style = self.style.SUCCESS
            elif status == 'Retrying':
                style = self.style.WARNING
            else:
                style = self.style.HTTP_INFO

            self.stdout.write(style(f'{status:.<40} {count:>5}'))

        self.stdout.write('='*60 + '\n')

    def cleanup_old_emails(self, days):
        """Delete old sent emails to free up space"""
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        
        deleted_count, _ = EmailTask.objects.filter(
            status=EmailTask.STATUS_SENT,
            updated_at__lt=cutoff_date
        ).delete()

        self.stdout.write(
            self.style.SUCCESS(
                f'✓ Cleaned up {deleted_count} old email task(s) (older than {days} days)'
            )
        )
