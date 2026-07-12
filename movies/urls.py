from django.urls import path
from . import views
urlpatterns=[
    path('',views.movie_list,name='movie_list'),
    path('<int:movie_id>/theaters',views.theater_list,name='theater_list'),
    path('theater/<int:theater_id>/seats/book/',views.book_seats,name='book_seats'),
    path('payments/<str:payment_id>/', views.payment_status, name='payment_status'),
    path('payments/webhook/', views.payment_webhook, name='payment_webhook'),
    path('admin-analytics/', views.admin_analytics, name='admin_analytics'),
]