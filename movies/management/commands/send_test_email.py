from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings


class Command(BaseCommand):
    help = 'Send a simple test email to verify email backend configuration'

    def add_arguments(self, parser):
        parser.add_argument('--to', required=True, help='Recipient email address')
        parser.add_argument('--subject', default='Test email from BookMySeat', help='Email subject')
        parser.add_argument('--body', default='This is a test email.', help='Email body')

    def handle(self, *args, **options):
        to = options['to']
        subject = options['subject']
        body = options['body']
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@bookmyseat.local')

        try:
            send_mail(subject, body, from_email, [to], fail_silently=False)
            self.stdout.write(self.style.SUCCESS(f'Successfully sent test email to {to} using backend {settings.EMAIL_BACKEND}'))
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f'Failed to send test email: {exc}'))
            raise
