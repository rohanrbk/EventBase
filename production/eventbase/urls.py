from django.contrib import admin
from django.urls import path
from core import views
urlpatterns=[path("admin/",admin.site.urls),path("",views.home),path("api/health",views.health),path("api/me",views.me),path("api/login",views.login_api),path("api/logout",views.logout_api),path("api/events",views.events_api),path("api/ops-state",views.ops_state),path("api/participant/summary",views.participant_summary),path("api/checkin",views.checkin),path("api/submission",views.submission),path("api/support",views.support),path("api/feedback",views.feedback)]
