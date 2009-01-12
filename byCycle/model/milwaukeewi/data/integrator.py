###############################################################################
# $Id: shp2pgsql.py 187 2006-08-16 01:26:11Z bycycle $
# Created 2006-09-07
#
# Milwaukee, WI, data integrator.
#
# Copyright (C) 2007-2008 Wyatt Baldwin, byCycle.org <wyatt@bycycle.org>.
# All rights reserved.
#
# For terms of use and warranty details, please see the LICENSE file included
# in the top level of this distribution. This software is provided AS IS with
# NO WARRANTY OF ANY KIND.
###############################################################################
from byCycle.model.data import integrator
from byCycle.model import milwaukeewi
from byCycle.model.milwaukeewi import data


class Integrator(integrator.Integrator):

    def __init__(self, *args, **kwargs):
        self.region_module = milwaukeewi
        self.region_data_module = data
        super(Integrator, self).__init__(*args, **kwargs)

    def get_state_code_for_city(self, city):
        return 'wi'
