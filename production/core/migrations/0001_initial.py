import core.models
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(name="Organization", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("name", models.CharField(max_length=140)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
        ]),
        migrations.CreateModel(name="Event", fields=[
            ("id", models.CharField(default=core.models.make_event_id, editable=False, max_length=24, primary_key=True, serialize=False)),
            ("name", models.CharField(max_length=120)),
            ("type", models.CharField(default="Other", max_length=60)),
            ("date", models.DateField()),
            ("format", models.CharField(default="Hybrid", max_length=40)),
            ("location", models.CharField(blank=True, max_length=160)),
            ("status", models.CharField(default="Draft", max_length=20)),
            ("share_code", models.CharField(default=core.models.make_code, max_length=12, unique=True)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="events", to="core.organization")),
        ]),
        migrations.CreateModel(name="Profile", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("role", models.CharField(choices=[("manager", "Manager"), ("participant", "Participant")], max_length=16)),
            ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="profiles", to="core.organization")),
            ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="eventbase_profile", to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.CreateModel(name="Membership", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("team", models.CharField(default="New team", max_length=100)),
            ("attendance", models.CharField(default="Online", max_length=40)),
            ("event", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="memberships", to="core.event")),
            ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="event_memberships", to=settings.AUTH_USER_MODEL)),
        ], options={"constraints": [models.UniqueConstraint(fields=("event", "user"), name="unique_event_member")]}),
        migrations.CreateModel(name="CheckIn", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("checked_in_at", models.DateTimeField(auto_now=True)),
            ("event", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="core.event")),
            ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
        ], options={"constraints": [models.UniqueConstraint(fields=("event", "user"), name="unique_event_checkin")]}),
        migrations.CreateModel(name="Submission", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("project_name", models.CharField(max_length=160)),
            ("project_summary", models.TextField(max_length=5000)),
            ("demo_url", models.URLField(blank=True, max_length=500)),
            ("repo_url", models.URLField(blank=True, max_length=500)),
            ("files_json", models.JSONField(default=list)),
            ("status", models.CharField(default="Draft", max_length=20)),
            ("updated_at", models.DateTimeField(auto_now=True)),
            ("event", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="core.event")),
            ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
        ], options={"constraints": [models.UniqueConstraint(fields=("event", "user"), name="unique_event_submission")]}),
        migrations.CreateModel(name="SupportRequest", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("category", models.CharField(max_length=80)),
            ("message", models.TextField(max_length=2000)),
            ("kind", models.CharField(default="mentor", max_length=24)),
            ("status", models.CharField(default="Received", max_length=24)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("event", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="support_requests", to="core.event")),
            ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.CreateModel(name="Feedback", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("rating", models.PositiveSmallIntegerField()),
            ("message", models.TextField(blank=True, max_length=2000)),
            ("created_at", models.DateTimeField(auto_now=True)),
            ("event", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="core.event")),
            ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
        ], options={"constraints": [models.UniqueConstraint(fields=("event", "user"), name="unique_event_feedback")]}),
        migrations.CreateModel(name="OperationsState", fields=[
            ("event", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name="operations_state", serialize=False, to="core.event")),
            ("payload", models.JSONField(default=dict)),
            ("updated_at", models.DateTimeField(auto_now=True)),
        ]),
    ]
