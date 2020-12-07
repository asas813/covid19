from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('covid19/', views.home, name='covid19'),
]