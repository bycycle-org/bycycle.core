###############################################################################
# $Id$
# Created 2005-11-07
#
# Top level of the byCycle Core package.
#
# Copyright (C) 2006, 2007 Wyatt Baldwin, byCycle.org <wyatt@bycycle.org>.
# All rights reserved.
#
# For terms of use and warranty details, please see the LICENSE file included
# in the top level of this distribution. This software is provided AS IS with
# NO WARRANTY OF ANY KIND.
###############################################################################
from os.path import abspath, dirname, join
install_path = dirname(abspath(__file__))
model_path = join(install_path, 'model')
