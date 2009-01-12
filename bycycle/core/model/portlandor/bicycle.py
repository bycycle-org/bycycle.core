################################################################################ $Id$
# Created 2005-11-07.
#
# Portland, OR Bicycle Travel Mode.
#
# Copyright (C) 2006 Wyatt Baldwin, byCycle.org <wyatt@bycycle.org>.
# All rights reserved.
#
# For terms of use and warranty details, please see the LICENSE file included
# in the top level of this distribution. This software is provided AS IS with
# NO WARRANTY OF ANY KIND.
###############################################################################
"""Bicycle travel mode for Portland, OR, region."""
from bycycle.core.model import tmode
from bycycle.core.model.entities.util import float_decode


# Preferences
FASTER, SHORTER, FLATTER, SAFER, DEFAULT = range(5)

# This maps MAX street class codes to "normal" codes, for use with bike lanes
max_codes = {
    5301: 1300,
    5401: 1400,
    5501: 1500,
}


class TravelMode(tmode.TravelMode):
    """Bicycle travel mode for the Portland, OR, region."""

    def __init__(self, region, pref='default'):
        """

        ``pref`` `string`
            User's simple preference option. Can be empty or one of "default",
            "flatter", "safer", "shorter", or "faster".

        """
        tmode.TravelMode.__init__(self)

        global pct_slopes, mph_up, mph_down
        pct_slopes = [p*.01 for p in
                      (0,    0.65, 1.8, 3.7, 7,  12, 21,  500)]
        mph_up     =  (12.5, 11,   9.5, 7.5, 5,  3,  2.5, 2.5)
        mph_down   =  (12.5, 14,   17,  21,  26, 31, 32,  32)

        global edge_attrs_index, length_index, code_index, bikemode_index
        global abs_slp_index, up_frac_index, node_f_id_index
        global street_name_id_index
        edge_attrs_index = region.edge_attrs_index
        length_index = edge_attrs_index['length']
        code_index = edge_attrs_index['code']
        bikemode_index = edge_attrs_index['bikemode']
        abs_slp_index = edge_attrs_index['abs_slope']
        up_frac_index = edge_attrs_index['up_frac']
        node_f_id_index = edge_attrs_index['node_f_id']
        street_name_id_index = edge_attrs_index['street_name_id']

        try:
            pref = globals()[(pref or 'default').upper()]
        except KeyError:
            raise ValueError('Unknown travel mode: %s' % pref)

        global mu, mm, lt, mt, ht, ca, cca, ccca
        global blt, bmt, bht, bca, bcca, bccca
        global no_bm_lt, no_bm_mt, no_bm_ht, no_bm_ca, no_bm_cca, no_bm_ccca
        global xxx
        xxx = 1000
        if pref == SAFER:
            mu = .85
            mm = .9
            lt = 1
            mt = 2
            ht = 4
            ca = cca = ccca = xxx
            # bike lane
            blt = .75
            bmt = 1
            bht = 2
            bca = bcca = bccca = xxx
            # no bike mode
            mult = 3
            no_bm_lt = blt * mult
            no_bm_mt = bmt * mult
            no_bm_ht = bht * mult
            no_bm_ca = no_bm_cca = no_bm_ccca = xxx
        else:
            mult = 2
            mu = .85
            mm = .9
            lt = 1
            mt = 1.17
            ht = 1.33
            ca = 2.67
            cca = 10
            ccca = 100
            # bike lane
            blt = .75
            bmt = .875
            bht = 1
            bca = 2
            bcca = 3
            bccca = 4
            # no bike mode
            mult = 2
            no_bm_lt = blt * mult
            no_bm_mt = bmt * mult
            no_bm_ht = bht * mult
            no_bm_ca = bca * mult
            no_bm_cca = bcca * mult
            no_bm_ccca = bccca * mult

    def getEdgeWeight(self, v, edge_attrs, prev_edge_attrs):
        """Calculate weight for edge given it & last crossed edge's attrs."""
        length = edge_attrs[length_index] * float_decode
        code = edge_attrs[code_index]
        bikemode = edge_attrs[bikemode_index]
        slope = edge_attrs[abs_slp_index] * float_decode
        upfrac = edge_attrs[up_frac_index] * float_decode
        downfrac = 1 - upfrac
        node_f_id = edge_attrs[node_f_id_index]
        street_name_id = edge_attrs[street_name_id_index]

        # -- Calculate base weight of edge (in hours)

        # Length of edge that is uphill in from => to direction
        up_len = length * upfrac

        # Length of edge that is downhill in from => to direction
        down_len = length * (1.0 - upfrac)

        # Swap uphill and downhill lengths when traversing edge to => from
        if v != node_f_id:
            up_len, down_len = down_len, up_len

        # Based on the slope, calculate the speed of travel uphill and downhill
        # (up_spd & down_spd)
        if slope <= 0:
            # Slope is at or before start
            up_spd = mph_up[0]
            down_spd = mph_down[0]
        elif slope >= pct_slopes[-1]:
            # Slope is at or past end
            pct_past_end = slope / pct_slopes[-2]
            up_spd = mph_up[-1] / pct_past_end      # slower
            down_spd = mph_down[-1] * pct_past_end  # faster
        else:
            for i, u in enumerate(pct_slopes[1:]):
                if slope <= u:
                    l = pct_slopes[i]
                    break
            pct_past_l = (slope - l) / (u - l)
            mph_up_i, mph_up_j = mph_up[i], mph_up[i+1]
            up_spd = mph_up_i - (mph_up_i - mph_up_j) * pct_past_l
            mph_down_i, mph_down_j = mph_down[i], mph_down[i+1]
            down_spd = mph_down_i + (mph_down_j - mph_down_i) * pct_past_l

        # Based on uphill length and speed, calculate time to traverse uphill
        # part of edge
        up_time = up_len / up_spd
        # Likewise for downhill part of edge
        down_time = down_len / down_spd
        # Add those together for estimated total time to traverse edge
        hours = up_time + down_time

        # -- Adjust weight based on user preference
        if bikemode != 'n':
            # Adjust bike network street
            if   bikemode == 't':          hours *= mu
            elif bikemode == 'p':          hours *= mm
            elif bikemode == 'b':
                code = max_codes.get(code, code)
                # Adjust bike lane for traffic (est. from st. type)
                if   code in (1500, 1521): hours *= blt    #lt
                elif code == 1450:         hours *= bmt    #mt
                elif code == 1400:         hours *= bht    #ht
                elif code == 1300:         hours *= bca    #ca
                elif 1200 <= code < 1300:  hours *= bcca   #ca+
                elif 1100 <= code < 1200:  hours *= bccca  #ca++
                else:                      hours *= xxx    #?
            elif bikemode == 'l':          hours *= lt
            elif bikemode == 'm':          hours *= mt
            elif bikemode == 'h':          hours *= ht
            elif bikemode == 'c':          hours *= ca
            elif bikemode == 'x':          hours *= xxx
            else:                          hours *= xxx
        else:
            # Adjust normal (i.e., no bikemode) street based on traffic
            # (est. from st. type)
            if code == 3200:                 hours *= mu
            elif code in (3230, 3240, 3250): hours *= mm
            else:
                if code in (1500, 1521):     hours *= no_bm_lt
                elif code == 1450:           hours *= no_bm_mt
                elif code == 1400:           hours *= no_bm_ht
                elif code == 1300:           hours *= no_bm_ca
                elif 1200 <= code < 1300:    hours *= no_bm_cca
                elif 1100 <= code < 1200:    hours *= no_bm_ccca
                else:                        hours *= xxx

        # Penalize edge if it has different street name from previous edge
        try:
            prev_ix_sn = prev_edge_attrs[street_name_id_index]
            if street_name_id != prev_ix_sn:
                hours += .0027777  # 10 seconds
        except TypeError:
            pass

        return hours
