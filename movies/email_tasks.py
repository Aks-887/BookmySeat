import logging
import threading
from datetime import timedelta

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from django.db import transaction

from .models import EmailTask

logger = logging.getLogger(__name__)

EMAIL_RETRY_BACKOFF = [1, 5, 15, 60]  # minutes delay for retries
EMAIL_MAX_ATTEMPTS = 5


def _sanitize_context(context: dict) -> dict:
    """Remove sensitive data from context before logging/storing"""
    sensitive_keys = ['password', 'token', 'secret', 'key', 'credential']
    sanitized = context.copy()
    
    for key in sensitive_keys:
        if key in sanitized:
            sanitized[key] = '***REDACTED***'
    
    return sanitized


def _send_email_task(task: EmailTask) -> None:
    """
    Send a single email task with error handling and retry logic.
    
    This function:
    - Updates task status to SENDING
    - Renders email templates with context
    - Sends via configured email backend
    - Logs success/failure with monitoring data
    - Schedules retries on failure using exponential backoff
    """
    if task.status == EmailTask.STATUS_SENT:
        logger.debug('EmailTask %s already sent, skipping', task.id)
        return

    try:
        task.status = EmailTask.STATUS_SENDING
        task.attempts += 1
        task.updated_at = timezone.now()
        task.save(update_fields=['status', 'attempts', 'updated_at'])

        subject = task.subject
        recipient = task.recipient
        context = task.context or {}

        # Render templates with context
        try:
            html_body = render_to_string(task.template_name, context)
            text_body = render_to_string(
                task.template_name.replace('.html', '.txt'), 
                context
            )
        except Exception as template_exc:
            logger.error(
                'Template rendering failed for EmailTask %s (recipient: %s): %s',
                task.id,
                recipient,
                str(template_exc),
                extra={'task_id': task.id, 'recipient': recipient}
            )
            raise

        # Create and send email message
        message = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@bookmyseat.local'),
            to=[recipient],
        )
        message.attach_alternative(html_body, "text/html")

        try:
            message.send(fail_silently=False)
            task.status = EmailTask.STATUS_SENT
            task.last_error = ''
            task.next_attempt_at = timezone.now()
            task.save(update_fields=['status', 'last_error', 'next_attempt_at'])
            
            logger.info(
                'Booking confirmation email sent successfully (EmailTask: %s, Recipient: %s, Attempts: %d)',
                task.id,
                recipient,
                task.attempts,
                extra={
                    'task_id': task.id,
                    'recipient': recipient,
                    'status': 'sent',
                    'attempts': task.attempts
                }
            )
        except Exception as send_exc:
            raise send_exc

    except Exception as exc:
        logger.warning(
            'Failed to send email for EmailTask %s (recipient: %s, attempt %d/%d): %s',
            task.id,
            task.recipient,
            task.attempts,
            task.max_attempts,
            str(exc),
            extra={
                'task_id': task.id,
                'recipient': task.recipient,
                'attempt': task.attempts,
                'max_attempts': task.max_attempts,
                'error': str(exc)
            },
            exc_info=True
        )
        
        task.last_error = str(exc)[:500]  # Truncate error message

        # Determine next status based on attempt count
        if task.attempts >= task.max_attempts:
            task.status = EmailTask.STATUS_FAILED
            task.next_attempt_at = timezone.now()
            logger.error(
                'EmailTask %s marked as FAILED after %d attempts (recipient: %s)',
                task.id,
                task.attempts,
                task.recipient,
                extra={
                    'task_id': task.id,
                    'recipient': task.recipient,
                    'final_status': 'failed'
                }
            )
        else:
            task.status = EmailTask.STATUS_RETRYING
            backoff_minutes = EMAIL_RETRY_BACKOFF[
                min(task.attempts - 1, len(EMAIL_RETRY_BACKOFF) - 1)
            ]
            task.next_attempt_at = timezone.now() + timedelta(
                minutes=backoff_minutes
            )
            logger.info(
                'EmailTask %s scheduled for retry in %d minutes (recipient: %s, next attempt: %s)',
                task.id,
                backoff_minutes,
                task.recipient,
                task.next_attempt_at,
                extra={
                    'task_id': task.id,
                    'recipient': task.recipient,
                    'retry_scheduled': True,
                    'retry_in_minutes': backoff_minutes
                }
            )

        task.save(update_fields=['status', 'last_error', 'next_attempt_at'])


def queue_booking_confirmation_email(recipient_email: str, booking_context: dict) -> EmailTask:
    """
    Queue a booking confirmation email for asynchronous sending.
    
    Args:
        recipient_email: The email address of the recipient
        booking_context: Dictionary containing booking information for template rendering
    
    Returns:
        EmailTask instance
    
    This function:
    - Validates the recipient email
    - Creates an EmailTask record with the context
    - Spawns a daemon thread to send immediately
    - Does NOT block the booking API response
    - Stores context for template rendering (no sensitive data)
    """
    # Validate recipient
    if not recipient_email or '@' not in recipient_email:
        logger.error(
            'Invalid recipient email provided: %s',
            recipient_email,
            extra={'recipient': recipient_email}
        )
        raise ValueError(f'Invalid email address: {recipient_email}')

    # Sanitize context before storage (remove sensitive data)
    sanitized_context = _sanitize_context(booking_context)

    task = EmailTask.objects.create(
        recipient=recipient_email,
        subject='Your Movie Ticket Confirmation - BookMySeat',
        template_name='emails/booking_confirmation.html',
        context=sanitized_context,  # store sanitized context
        max_attempts=EMAIL_MAX_ATTEMPTS,
    )
    
    logger.info(
        'Booking confirmation email queued (EmailTask: %s, Recipient: %s)',
        task.id,
        recipient_email,
        extra={
            'task_id': task.id,
            'recipient': recipient_email,
            'template': 'booking_confirmation',
            'queued_at': timezone.now().isoformat()
        }
    )

    # Dispatch in background thread (non-blocking)
    thread = threading.Thread(
        target=_dispatch_email_task_async,
        args=(task.id,),
        daemon=True
    )
    thread.start()
    
    return task


def _dispatch_email_task_async(task_id: int) -> None:
    """
    Dispatch an email task asynchronously in a background thread.
    
    Args:
        task_id: The ID of the EmailTask to dispatch
    """
    try:
        task = EmailTask.objects.get(pk=task_id)
        _send_email_task(task)
    except EmailTask.DoesNotExist:
        logger.warning(
            'EmailTask %s not found during async dispatch',
            task_id,
            extra={'task_id': task_id}
        )
    except Exception as exc:
        logger.error(
            'Unexpected error during async email dispatch for task %s: %s',
            task_id,
            str(exc),
            extra={'task_id': task_id},
            exc_info=True
        )


def process_pending_email_tasks(limit: int = 20) -> int:
    """
    Process pending and retrying email tasks from the queue.
    
    This function should be called periodically (e.g., via cron job or Celery).
    
    Args:
        limit: Maximum number of tasks to process in one batch
    
    Returns:
        Number of tasks successfully processed
    
    Features:
    - Uses database locking to prevent duplicate sends
    - Respects next_attempt_at timing
    - Logs all processing activity for monitoring
    """
    now = timezone.now()
    
    # Fetch pending and retrying tasks that are ready
    tasks = EmailTask.objects.filter(
        status__in=[EmailTask.STATUS_PENDING, EmailTask.STATUS_RETRYING],
        next_attempt_at__lte=now,
    ).order_by('next_attempt_at')[:limit]

    count = 0
    failed_count = 0
    
    logger.info(
        'Starting email queue processing: %d tasks available',
        tasks.count(),
        extra={'available_tasks': tasks.count()}
    )

    for task in tasks:
        try:
            with transaction.atomic():
                # Use select_for_update to prevent concurrent processing
                task = EmailTask.objects.select_for_update().get(pk=task.pk)
                _send_email_task(task)
                count += 1
        except EmailTask.DoesNotExist:
            continue
        except Exception as exc:
            failed_count += 1
            logger.error(
                'Error processing EmailTask %s: %s',
                task.pk,
                str(exc),
                extra={'task_id': task.pk},
                exc_info=True
            )

    logger.info(
        'Email queue processing complete: %d sent, %d failed',
        count,
        failed_count,
        extra={'processed': count, 'failed': failed_count}
    )

    return count


def get_email_task_stats() -> dict:
    """
    Get statistics about email task processing.
    
    Returns:
        Dictionary containing counts by status
    """
    stats = {}
    for status_code, status_label in EmailTask.STATUS_CHOICES:
        count = EmailTask.objects.filter(status=status_code).count()
        stats[status_label] = count
    
    logger.debug('Email task statistics: %s', stats)
    return stats
