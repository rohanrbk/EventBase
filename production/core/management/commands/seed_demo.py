from datetime import date
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import Organization,Profile,Event,Membership
class Command(BaseCommand):
 help="Create the fictional EventBase judging demo workspace and accounts."
 def handle(self,*args,**options):
  org,_=Organization.objects.get_or_create(name="EventBase Demo Organization")
  User=get_user_model()
  manager,_=User.objects.get_or_create(username="manager@eventbase.demo",defaults={"email":"manager@eventbase.demo","first_name":"Alex","last_name":"Morgan"})
  manager.email="manager@eventbase.demo";manager.first_name="Alex";manager.last_name="Morgan";manager.set_password("eventbase-demo");manager.save()
  Profile.objects.update_or_create(user=manager,defaults={"organization":org,"role":"manager"})
  participant,_=User.objects.get_or_create(username="jordan@eventbase.demo",defaults={"email":"jordan@eventbase.demo","first_name":"Jordan","last_name":"Patel"})
  participant.set_unusable_password();participant.save()
  Profile.objects.update_or_create(user=participant,defaults={"organization":org,"role":"participant"})
  e1,_=Event.objects.get_or_create(pk="EV-01",defaults={"organization":org,"name":"Hack the Future 2026","type":"Hackathon","date":date(2026,11,14),"format":"Hybrid","location":"The Foundry · Bengaluru","status":"Live","share_code":"FUTURE25"})
  e2,_=Event.objects.get_or_create(pk="EV-02",defaults={"organization":org,"name":"AI for Earth Summit","type":"Conference","date":date(2026,12,4),"format":"In-person","location":"Mumbai · The NCPA","status":"Upcoming","share_code":"EARTH26"})
  Membership.objects.get_or_create(event=e1,user=participant,defaults={"team":"Team Orbit","attendance":"Online"})
  self.stdout.write(self.style.SUCCESS("Demo ready: manager@eventbase.demo / eventbase-demo; participant access code FUTURE25"))
