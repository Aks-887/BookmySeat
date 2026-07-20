from django.urls import path
from . import views
urlpatterns=[
    path('',views.movie_list,name='movie_list'),
    path('autocomplete/',views.movies_autocomplete,name='movies_autocomplete'),
    path('<int:movie_id>/theaters',views.theater_list,name='theater_list'),
    path('theater/<int:theater_id>/seats/book/',views.book_seats,name='book_seats'),
    path('payments/checkout/<str:payment_id>/', views.payment_checkout, name='payment_checkout'),
    path('payments/confirm/', views.confirm_payment, name='confirm_payment'),
    path('payments/webhook/', views.payment_webhook, name='payment_webhook'),
    path('payments/<str:payment_id>/', views.payment_status, name='payment_status'),
    path('webhooks/sendgrid/events/', views.sendgrid_events_webhook, name='sendgrid_events_webhook'),
    path('admin-analytics/', views.admin_analytics, name='admin_analytics'),
    path('cancel/<int:booking_id>/', views.cancel_booking, name='cancel_booking'),
]
