import json,logging
from datetime import date
from django.contrib.auth import authenticate,get_user_model,login,logout
from django.db import connection
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET,require_POST,require_http_methods
from .models import Organization,Profile,Event,Membership,CheckIn,Submission,SupportRequest,Feedback,OperationsState
log=logging.getLogger(__name__); User=get_user_model()
def err(message,status=400): return JsonResponse({"error":message},status=status)
def body(request):
 try:
  value=json.loads(request.body or b"{}")
  return value if isinstance(value,dict) else None
 except (json.JSONDecodeError,UnicodeDecodeError): return None
def actor(request,role=None):
 if not request.user.is_authenticated:return None,err("Sign in required",401)
 try:p=request.user.eventbase_profile
 except Profile.DoesNotExist:return None,err("Account profile is unavailable",403)
 if role and p.role!=role:return None,err("This role cannot access that action",403)
 return (request.user,p),None
def user_data(user):return {"name":user.get_full_name() or user.username,"email":user.email,"role":user.eventbase_profile.role}
def event_data(event):return {"id":event.id,"name":event.name,"type":event.type,"date":event.date.isoformat(),"format":event.format,"location":event.location,"status":event.status,"participants":event.memberships.count(),"share_code":event.share_code}
def linked_event(request,user):
 try:return Event.objects.get(pk=request.session.get("event_id"),organization=user.eventbase_profile.organization,memberships__user=user)
 except Event.DoesNotExist:return None
@ensure_csrf_cookie
@require_GET
def home(request):return render(request,"index.html")
@require_GET
def health(request):
 try:
  connection.ensure_connection()
  return JsonResponse({"ok":True,"product":"EventBase"})
 except Exception:
  log.exception("Health check failed")
  return err("Service unavailable",503)
@require_GET
def me(request):
 if not request.user.is_authenticated:return JsonResponse({"authenticated":False})
 result={"authenticated":True,"user":user_data(request.user)}
 if request.session.get("event_id"):result["event_id"]=request.session["event_id"]
 return JsonResponse(result)
@require_POST
def login_api(request):
 data=body(request)
 if data is None:return err("Invalid JSON request")
 email=str(data.get("email","")).strip().lower(); role=data.get("role")
 if "@" not in email or role not in ("manager","participant"):return err("Enter a valid email and choose a role")
 event=None
 if role=="manager":
  username=User.objects.filter(email__iexact=email).values_list("username",flat=True).first() or email
  user=authenticate(request,username=username,password=str(data.get("password","")))
  if not user:return err("Email or password is incorrect",401)
  try:p=user.eventbase_profile
  except Profile.DoesNotExist:return err("Manager account is not configured",403)
  if p.role!="manager":return err("Email or password is incorrect",401)
 else:
  try:event=Event.objects.get(share_code__iexact=str(data.get("event_code","")).strip())
  except Event.DoesNotExist:return err("That event access code was not found",401)
  with transaction.atomic():
   user=User.objects.filter(email__iexact=email).first()
   if user:
    try:p=user.eventbase_profile
    except Profile.DoesNotExist:return err("Account profile is unavailable",403)
    if p.role!="participant" or p.organization_id!=event.organization_id:return err("This account cannot join this event",403)
   else:
    user=User.objects.create_user(username=email,email=email,first_name=str(data.get("name",email.split("@")[0]))[:150],password=None)
    user.set_unusable_password();user.save(update_fields=["password"])
    Profile.objects.create(user=user,organization=event.organization,role="participant")
   Membership.objects.get_or_create(event=event,user=user,defaults={"team":"New team","attendance":"Online"})
 login(request,user);request.session.cycle_key()
 if event:request.session["event_id"]=event.id
 else:request.session.pop("event_id",None)
 return JsonResponse({"authenticated":True,"user":user_data(user),"event_id":event.id if event else None})
@require_POST
def logout_api(request):logout(request);return JsonResponse({"ok":True})
@require_http_methods(["GET","POST"])
def events_api(request):
 pair,e=actor(request)
 if e:return e
 user,p=pair
 if request.method=="POST":
  if p.role!="manager":return err("This role cannot access that action",403)
  d=body(request)
  if d is None:return err("Invalid JSON request")
  try:date_value=date.fromisoformat(str(d.get("date","")))
  except ValueError:return err("Enter a valid event date")
  name=str(d.get("name","")).strip();location=str(d.get("location","")).strip()
  if not name or len(name)>120 or len(location)>160:return err("Enter an event name and valid details")
  event=Event.objects.create(organization=p.organization,name=name,type=str(d.get("type","Other"))[:60],date=date_value,format=str(d.get("format","Hybrid"))[:40],location=location)
  return JsonResponse({"event":event_data(event)},status=201)
 qs=Event.objects.filter(organization=p.organization)
 if p.role=="participant":qs=qs.filter(memberships__user=user)
 return JsonResponse({"events":[event_data(x) for x in qs.order_by("-date").distinct()]})
@require_http_methods(["GET","POST"])
def ops_state(request):
 pair,e=actor(request,"manager")
 if e:return e
 p=pair[1]
 if request.method=="POST":
  d=body(request)
  if d is None or not isinstance(d.get("state"),dict):return err("State object is required")
  event=Event.objects.filter(pk=str(d.get("event_id","")),organization=p.organization).first()
  if not event:return err("Event not found",404)
  OperationsState.objects.update_or_create(event=event,defaults={"payload":d["state"]})
  return JsonResponse({"saved":True})
 event=Event.objects.filter(pk=request.GET.get("event_id"),organization=p.organization).first()
 if not event:return err("Event not found",404)
 row=OperationsState.objects.filter(event=event).first()
 return JsonResponse({"state":row.payload if row else None})
@require_GET
def participant_summary(request):
 pair,e=actor(request,"participant")
 if e:return e
 user=pair[0];event=linked_event(request,user)
 if not event:return err("No event linked to this participant",404)
 member=Membership.objects.get(event=event,user=user);check=CheckIn.objects.filter(event=event,user=user).first()
 sub=Submission.objects.filter(event=event,user=user).first()
 req=[{"id":r.pk,"category":r.category,"message":r.message,"kind":r.kind,"status":r.status,"created_at":r.created_at.isoformat()} for r in SupportRequest.objects.filter(event=event,user=user).order_by("-created_at")]
 fb=Feedback.objects.filter(event=event,user=user).first()
 submission_data={"project_name":sub.project_name,"project_summary":sub.project_summary,"demo_url":sub.demo_url,"repo_url":sub.repo_url,"files_json":json.dumps(sub.files_json),"status":sub.status} if sub else None
 return JsonResponse({"event_id":event.id,"team":member.team,"attendance":member.attendance,"checked_in":bool(check),"submission":submission_data,"support_requests":req,"feedback":{"rating":fb.rating,"message":fb.message} if fb else None})
@require_POST
def checkin(request):
 pair,e=actor(request,"participant")
 if e:return e
 user=pair[0];event=linked_event(request,user)
 if not event:return err("No event is linked to this participant",400)
 CheckIn.objects.update_or_create(event=event,user=user)
 return JsonResponse({"checked_in":True})
@require_POST
def submission(request):
 pair,e=actor(request,"participant")
 if e:return e
 d=body(request)
 if d is None:return err("Invalid JSON request")
 user=pair[0];event=linked_event(request,user);name=str(d.get("project_name","")).strip();summary=str(d.get("project_summary","")).strip()
 if not event or not name or not summary:return err("An event, project name, and summary are required")
 files=[str(x)[:180] for x in d.get("files",[])[:10]] if isinstance(d.get("files",[]),list) else []
 row,_=Submission.objects.update_or_create(event=event,user=user,defaults={"project_name":name[:160],"project_summary":summary[:5000],"demo_url":str(d.get("demo_url",""))[:500],"repo_url":str(d.get("repo_url",""))[:500],"files_json":files,"status":"Submitted" if d.get("submit") else "Draft"})
 return JsonResponse({"status":row.status,"updated_at":row.updated_at.isoformat(),"files_recorded":files,"uploaded":False})
@require_http_methods(["GET","POST"])
def support(request):
 pair,e=actor(request)
 if e:return e
 user,p=pair
 if request.method=="POST":
  if p.role!="participant":return err("This role cannot access that action",403)
  d=body(request)
  if d is None:return err("Invalid JSON request")
  event=linked_event(request,user);message=str(d.get("message","")).strip()
  if not event or not message:return err("An event and support message are required")
  row=SupportRequest.objects.create(event=event,user=user,category=str(d.get("category","General help"))[:80],message=message[:2000],kind=str(d.get("kind","mentor"))[:24])
  return JsonResponse({"id":row.pk,"status":row.status,"stored":True,"staff_notified":False},status=201)
 qs=SupportRequest.objects.select_related("user","event")
 if p.role=="manager":qs=qs.filter(event__organization=p.organization)
 else:qs=qs.filter(user=user)
 requests=[{"id":r.pk,"category":r.category,"message":r.message,"kind":r.kind,"status":r.status,"created_at":r.created_at.isoformat(),"participant":r.user.get_full_name() or r.user.email} for r in qs.order_by("-created_at")[:200]]
 return JsonResponse({"requests":requests})
@require_POST
def feedback(request):
 pair,e=actor(request,"participant")
 if e:return e
 d=body(request)
 if d is None:return err("Invalid JSON request")
 try:rating=int(d.get("rating",0))
 except (TypeError,ValueError):rating=0
 user=pair[0];event=linked_event(request,user)
 if not event or not 1<=rating<=5:return err("Select a rating from 1 to 5")
 Feedback.objects.update_or_create(event=event,user=user,defaults={"rating":rating,"message":str(d.get("message",""))[:2000]})
 return JsonResponse({"saved":True})


