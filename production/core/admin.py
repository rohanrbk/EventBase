from django.contrib import admin
from .models import Organization,Profile,Event,Membership,CheckIn,Submission,SupportRequest,Feedback,OperationsState
admin.site.register([Organization,Profile,Event,Membership,CheckIn,Submission,SupportRequest,Feedback,OperationsState])
