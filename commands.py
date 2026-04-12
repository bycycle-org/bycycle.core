from typing import Annotated

from runcommands import arg, command
from runcommands import commands as c

from bycycle.core.commands import *


@command
def django(
    *args: Annotated[
        str,
        arg(help="Django command, args, and options (specify options after --)"),
    ],
):
    """Run a Django command

    Runs `django-admin` with `DJANGO_SETTINGS_MODULE` set to `bycycle.core.settings`.

    Options for the Django command must be specified after `--`:

        run django migrate -- --help

    """
    c.local(
        ("uv", "run", "django-admin", *args),
        environ={"DJANGO_SETTINGS_MODULE": "bycycle.core.settings"},
        echo=True,
    )
