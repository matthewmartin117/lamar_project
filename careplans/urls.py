from django.urls import path
from .views import intake_order

urlpatterns = [
    path("intake/", intake_order, name="intake"),
]
