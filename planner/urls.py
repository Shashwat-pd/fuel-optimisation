from django.urls import path

from planner.views import RouteView

urlpatterns = [
    path("route/", RouteView.as_view()),
]
