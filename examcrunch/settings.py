from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-a=(cedd+7w2ghwpt8g#e##y0gouk#r2te$5phmusj!a)=n2zc$'

DEBUG = True

ALLOWED_HOSTS = []

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'accounts',
    'courses',
    'helpdesk',
    'studygroups',
]

AUTH_USER_MODEL = 'accounts.User'

AUTHENTICATION_BACKENDS = [
    'accounts.backends.EmailBackend',
    'django.contrib.auth.backends.ModelBackend',
]

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'my_courses'
LOGOUT_REDIRECT_URL = 'home'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'examcrunch.urls'

TEMPLATES = [
    {
        'BACKEND':'django.template.backends.django.DjangoTemplates',
        'DIRS':[BASE_DIR / 'templates'],
        'APP_DIRS':True,
        'OPTIONS':{
            'context_processors':[
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'helpdesk.views.inbox_badge',
            ],
        },
    },
]

WSGI_APPLICATION = 'examcrunch.wsgi.application'

DATABASES = {
    'default':{
        'ENGINE':'django.db.backends.sqlite3',
        'NAME':BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME':'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
        'OPTIONS':{
            'user_attributes':('username','first_name','last_name','email','student_id'),
        },
    },
    {
        'NAME':'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME':'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME':'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Dhaka'

USE_I18N = True

USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

import tempfile
PRIVATE_MEDIA_ROOT = BASE_DIR / 'private_media'
RESOURCE_MAX_MB = 5
RESOURCE_ALLOWED_EXTENSIONS = ['pdf','doc','docx','ppt','pptx','xls','xlsx',
                               'txt','png','jpg','jpeg','zip']

from django.contrib.messages import constants as message_constants
MESSAGE_TAGS = {message_constants.ERROR:'danger'}

MIN_RATINGS_FOR_DASHBOARD = 3
MAX_ACTIVE_HELPS = 2
INVITATION_EXPIRY_HOURS = 48
MAX_PENDING_INVITATIONS = 3
GROUP_SUGGESTION_THRESHOLD = 3
MAX_GROUP_MEMBERS = 6

import sys
if 'test' in sys.argv:
    PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']

    PRIVATE_MEDIA_ROOT = tempfile.mkdtemp(prefix='examcrunch_private_')
    MEDIA_ROOT = tempfile.mkdtemp(prefix='examcrunch_media_')

MAILERS = {
    'default':{
        'BACKEND':'django.core.mail.backends.console.EmailBackend',
    },
}
