from django.apps import AppConfig as BaseAppConfig


class AppConfig(BaseAppConfig):
    name = "bycycle.core"
    label = "bycycle_core"
    verbose_name = "byCycle Core"
