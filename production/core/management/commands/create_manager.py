from django.core.management.base import BaseCommand,CommandError
from django.contrib.auth import get_user_model
from core.models import Organization,Profile
class Command(BaseCommand):
 help="Create a manager login scoped to an organization."
 def add_arguments(self,parser):
  parser.add_argument("--email",required=True);parser.add_argument("--password",required=True);parser.add_argument("--organization",required=True)
 def handle(self,*args,**opts):
  email=opts["email"].strip().lower();password=opts["password"]
  if len(password)<12:raise CommandError("Use a password with at least 12 characters.")
  User=get_user_model()
  if User.objects.filter(email__iexact=email).exists():raise CommandError("That email already has an account.")
  org,_=Organization.objects.get_or_create(name=opts["organization"].strip())
  user=User.objects.create_user(username=email,email=email,password=password,first_name=email.split("@")[0][:150])
  Profile.objects.create(user=user,organization=org,role="manager")
  self.stdout.write(self.style.SUCCESS(f"Manager account created for {email} in {org.name}."))
