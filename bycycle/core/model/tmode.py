################################################################################
# $Id$
# Created 2006-09-13.
#
# Base for travel modes.
#
# Copyright (C) 2006 Wyatt Baldwin, byCycle.org <wyatt@bycycle.org>.
# All rights reserved.
# 
# For terms of use and warranty details, please see the LICENSE file included
# in the top level of this distribution. This software is provided AS IS with
# NO WARRANTY OF ANY KIND.
################################################################################
class TravelMode(object):
    
    def __init__(self):
        pass
    
    def getEdgeWeight(self, v, edge_attrs, prev_edge_attrs):
        length = edge_attrs[self.indices['length']]
        return length
        
    getHeuristicWeight = None