import secrets,uuid
from django.conf import settings
from django.db import models
def make_code(): return secrets.token_hex(3).upper()
def make_event_id(): return "EV-"+uuid.uuid4().hex[:8].upper()
class Organization(models.Model):
 name=models.CharField(max_length=140)
 created_at=models.DateTimeField(auto_now_add=True)
class Profile(models.Model):
 user=models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="eventbase_profile")
 organization=models.ForeignKey(Organization,on_delete=models.CASCADE,related_name="profiles")
 role=models.CharField(max_length=16,choices=[("manager","Manager"),("participant","Participant")])
class Event(models.Model):
 id=models.CharField(primary_key=True,max_length=24,default=make_event_id,editable=False)
 organization=models.ForeignKey(Organization,on_delete=models.CASCADE,related_name="events")
 name=models.CharField(max_length=120); type=models.CharField(max_length=60,default="Other")
 date=models.DateField(); format=models.CharField(max_length=40,default="Hybrid"); location=models.CharField(max_length=160,blank=True)
 status=models.CharField(max_length=20,default="Draft"); share_code=models.CharField(max_length=12,unique=True,default=make_code)
 created_at=models.DateTimeField(auto_now_add=True)
class Membership(models.Model):
 event=models.ForeignKey(Event,on_delete=models.CASCADE,related_name="memberships")
 user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="event_memberships")
 team=models.CharField(max_length=100,default="New team"); attendance=models.CharField(max_length=40,default="Online")
 class Meta: constraints=[models.UniqueConstraint(fields=["event","user"],name="unique_event_member")]
class CheckIn(models.Model):
 event=models.ForeignKey(Event,on_delete=models.CASCADE); user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
 checked_in_at=models.DateTimeField(auto_now=True)
 class Meta: constraints=[models.UniqueConstraint(fields=["event","user"],name="unique_event_checkin")]
class Submission(models.Model):
 event=models.ForeignKey(Event,on_delete=models.CASCADE); user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
 project_name=models.CharField(max_length=160); project_summary=models.TextField(max_length=5000); demo_url=models.URLField(max_length=500,blank=True); repo_url=models.URLField(max_length=500,blank=True)
 files_json=models.JSONField(default=list); status=models.CharField(max_length=20,default="Draft"); updated_at=models.DateTimeField(auto_now=True)
 class Meta: constraints=[models.UniqueConstraint(fields=["event","user"],name="unique_event_submission")]
class SupportRequest(models.Model):
 event=models.ForeignKey(Event,on_delete=models.CASCADE,related_name="support_requests"); user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
 category=models.CharField(max_length=80); message=models.TextField(max_length=2000); kind=models.CharField(max_length=24,default="mentor")
 status=models.CharField(max_length=24,default="Received"); created_at=models.DateTimeField(auto_now_add=True)
class Feedback(models.Model):
 event=models.ForeignKey(Event,on_delete=models.CASCADE); user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
 rating=models.PositiveSmallIntegerField(); message=models.TextField(max_length=2000,blank=True); created_at=models.DateTimeField(auto_now=True)
 class Meta: constraints=[models.UniqueConstraint(fields=["event","user"],name="unique_event_feedback")]
class OperationsState(models.Model):
 event=models.OneToOneField(Event,primary_key=True,on_delete=models.CASCADE,related_name="operations_state")
 payload=models.JSONField(default=dict); updated_at=models.DateTimeField(auto_now=True)

