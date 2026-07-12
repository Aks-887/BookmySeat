from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Q
from .models import EmailTask, Movie, Theater, Seat, Booking, MovieImage, Genre, Language
from .email_tasks import _send_email_task


class MovieImageInline(admin.TabularInline):
    model = MovieImage
    extra = 1


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')
    search_fields = ('name', 'code')


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ['name', 'rating', 'cast', 'release_date']
    inlines = [MovieImageInline]
    filter_horizontal = ('genres', 'languages')
    list_filter = ('rating', 'release_date', 'genres', 'languages')
    search_fields = ('name', 'cast', 'description')
    readonly_fields = ('release_date',)


@admin.register(Theater)
class TheaterAdmin(admin.ModelAdmin):
    list_display = ['name', 'movie', 'time']


@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ['theater', 'seat_number', 'is_booked']


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['user', 'seat', 'movie', 'theater', 'payment_id', 'booked_at']
    search_fields = ['user__username', 'payment_id', 'movie__name', 'theater__name']


@admin.register(EmailTask)
class EmailTaskAdmin(admin.ModelAdmin):
    """
    Admin interface for monitoring and managing email task queue.
    
    Features:
    - Color-coded status display
    - Quick filtering by status
    - Manual retry of failed emails
    - Detailed error tracking
    - Recipient search
    """
    list_display = [
        'recipient',
        'subject_short',
        'status_badge',
        'attempts',
        'max_attempts',
        'next_attempt_at',
        'created_at'
    ]
    list_filter = [
        'status',
        'created_at',
        'updated_at',
        'attempts'
    ]
    search_fields = ['recipient', 'subject', 'id']
    readonly_fields = [
        'id',
        'created_at',
        'updated_at',
        'context_display',
        'last_error_display'
    ]
    fieldsets = (
        ('Email Information', {
            'fields': ('id', 'recipient', 'subject', 'template_name')
        }),
        ('Status & Attempts', {
            'fields': ('status', 'attempts', 'max_attempts', 'last_error_display')
        }),
        ('Scheduling', {
            'fields': ('next_attempt_at',)
        }),
        ('Context (for debugging)', {
            'fields': ('context_display',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    actions = ['retry_failed_emails', 'mark_as_sent', 'delete_selected_tasks']
    ordering = ['-next_attempt_at', '-created_at']

    def subject_short(self, obj):
        """Display truncated subject"""
        return obj.subject[:50] + ('...' if len(obj.subject) > 50 else '')
    subject_short.short_description = 'Subject'

    def status_badge(self, obj):
        """Display color-coded status badge"""
        colors = {
            EmailTask.STATUS_PENDING: '#0099cc',
            EmailTask.STATUS_SENDING: '#ff9900',
            EmailTask.STATUS_SENT: '#00cc00',
            EmailTask.STATUS_RETRYING: '#ffcc00',
            EmailTask.STATUS_FAILED: '#cc0000',
        }
        color = colors.get(obj.status, '#666666')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def context_display(self, obj):
        """Display context as formatted JSON for debugging"""
        if not obj.context:
            return 'No context'
        import json
        try:
            formatted = json.dumps(obj.context, indent=2)
            return format_html('<pre style="max-height: 300px; overflow-y: auto;">{}</pre>', formatted)
        except:
            return str(obj.context)
    context_display.short_description = 'Context (JSON)'

    def last_error_display(self, obj):
        """Display last error with formatting"""
        if not obj.last_error:
            return '✓ No errors'
        return format_html(
            '<div style="background-color: #fff3cd; padding: 10px; border-radius: 4px; '
            'border-left: 4px solid #ffc107;"><pre style="margin: 0; white-space: pre-wrap;">{}</pre></div>',
            obj.last_error
        )
    last_error_display.short_description = 'Last Error'

    def retry_failed_emails(self, request, queryset):
        """Action to retry failed emails"""
        failed_tasks = queryset.filter(status=EmailTask.STATUS_FAILED)
        count = 0
        for task in failed_tasks:
            task.status = EmailTask.STATUS_RETRYING
            task.attempts = 0
            task.last_error = ''
            task.save(update_fields=['status', 'attempts', 'last_error'])
            count += 1
        
        self.message_user(
            request,
            f'✓ {count} failed email task(s) queued for retry'
        )
    retry_failed_emails.short_description = 'Retry selected failed emails'

    def mark_as_sent(self, request, queryset):
        """Action to manually mark emails as sent"""
        count = queryset.update(status=EmailTask.STATUS_SENT)
        self.message_user(
            request,
            f'✓ {count} email task(s) marked as sent'
        )
    mark_as_sent.short_description = 'Mark as sent'

    def delete_selected_tasks(self, request, queryset):
        """Action to delete selected email tasks"""
        count = queryset.count()
        queryset.delete()
        self.message_user(
            request,
            f'✓ {count} email task(s) deleted'
        )
    delete_selected_tasks.short_description = 'Delete selected email tasks'

    def get_queryset(self, request):
        """Order by next_attempt_at by default"""
        qs = super().get_queryset(request)
        return qs.order_by('-next_attempt_at', '-created_at')
    list_filter = ['status', 'created_at']
    search_fields = ['recipient', 'subject', 'last_error']
    readonly_fields = ['created_at', 'updated_at']
