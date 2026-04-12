DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": "bycycle",
        "USER": "bycycle",
        "PASSWORD": "bycycle",
    },
}

INSTALLED_APPS = [
    "bycycle.core.apps.AppConfig",
]
