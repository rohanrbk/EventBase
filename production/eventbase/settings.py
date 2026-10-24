import os
from pathlib import Path
from urllib.parse import urlparse
BASE_DIR=Path(__file__).resolve().parent.parent
SECRET_KEY=os.environ.get("DJANGO_SECRET_KEY", "")
DEBUG=os.environ.get("DEBUG","false").lower()=="true"
if not SECRET_KEY and DEBUG: SECRET_KEY="local-only-insecure-key-change-before-deploying"
if not SECRET_KEY: raise RuntimeError("DJANGO_SECRET_KEY must be set")
ALLOWED_HOSTS=[x.strip() for x in os.environ.get("ALLOWED_HOSTS","localhost,127.0.0.1").split(",") if x.strip()]
INSTALLED_APPS=["django.contrib.admin","django.contrib.auth","django.contrib.contenttypes","django.contrib.sessions","django.contrib.messages","django.contrib.staticfiles","core"]
MIDDLEWARE=["django.middleware.security.SecurityMiddleware","whitenoise.middleware.WhiteNoiseMiddleware","django.contrib.sessions.middleware.SessionMiddleware","django.middleware.common.CommonMiddleware","core.middleware.NoStoreAPIMiddleware","django.middleware.csrf.CsrfViewMiddleware","django.contrib.auth.middleware.AuthenticationMiddleware","django.contrib.messages.middleware.MessageMiddleware","django.middleware.clickjacking.XFrameOptionsMiddleware"]
ROOT_URLCONF="eventbase.urls"
TEMPLATES=[{"BACKEND":"django.template.backends.django.DjangoTemplates","DIRS":[BASE_DIR/"templates"],"APP_DIRS":True,"OPTIONS":{"context_processors":["django.template.context_processors.request","django.contrib.auth.context_processors.auth","django.contrib.messages.context_processors.messages"]}}]
WSGI_APPLICATION="eventbase.wsgi.application"
DATABASE_URL=os.environ.get("DATABASE_URL","")
if DATABASE_URL.startswith(("postgres://","postgresql://")):
 db=urlparse(DATABASE_URL)
 DATABASES={"default":{"ENGINE":"django.db.backends.postgresql","NAME":db.path.lstrip("/"),"USER":db.username or "","PASSWORD":db.password or "","HOST":db.hostname or "","PORT":db.port or 5432,"CONN_MAX_AGE":60,"OPTIONS":{"sslmode":os.environ.get("DB_SSLMODE","prefer")}}}
else: DATABASES={"default":{"ENGINE":"django.db.backends.sqlite3","NAME":BASE_DIR/"data"/"eventbase.sqlite3"}}
AUTH_PASSWORD_VALIDATORS=[{"NAME":"django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},{"NAME":"django.contrib.auth.password_validation.MinimumLengthValidator"},{"NAME":"django.contrib.auth.password_validation.CommonPasswordValidator"},{"NAME":"django.contrib.auth.password_validation.NumericPasswordValidator"}]
LANGUAGE_CODE="en-us"; TIME_ZONE="Asia/Kolkata"; USE_I18N=True; USE_TZ=True
STATIC_URL="/static/"; STATIC_ROOT=BASE_DIR/"staticfiles"; STATICFILES_DIRS=[BASE_DIR/"static"]
STORAGES={"default":{"BACKEND":"django.core.files.storage.FileSystemStorage"},"staticfiles":{"BACKEND":"whitenoise.storage.CompressedManifestStaticFilesStorage"}}
DEFAULT_AUTO_FIELD="django.db.models.BigAutoField"
SESSION_COOKIE_NAME="eventbase_session"; SESSION_COOKIE_HTTPONLY=True; SESSION_COOKIE_SAMESITE="Lax"; SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE",str(not DEBUG)).lower()=="true"
CSRF_COOKIE_SECURE=os.environ.get("COOKIE_SECURE",str(not DEBUG)).lower()=="true"; CSRF_COOKIE_SAMESITE="Lax"; SECURE_CONTENT_TYPE_NOSNIFF=True; SECURE_REFERRER_POLICY="same-origin"; X_FRAME_OPTIONS="DENY"
SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO","https")
SECURE_SSL_REDIRECT=os.environ.get("SECURE_SSL_REDIRECT","false").lower()=="true"
SECURE_HSTS_SECONDS=int(os.environ.get("SECURE_HSTS_SECONDS","0"))
CSRF_TRUSTED_ORIGINS=[x.strip() for x in os.environ.get("CSRF_TRUSTED_ORIGINS","").split(",") if x.strip()]
DEMO_MODE=os.environ.get("DEMO_MODE","false").lower()=="true"
DATA_UPLOAD_MAX_MEMORY_SIZE=1_000_000
LOGGING={"version":1,"disable_existing_loggers":False,"handlers":{"console":{"class":"logging.StreamHandler"}},"root":{"handlers":["console"],"level":os.environ.get("LOG_LEVEL","INFO")}}




