def bicycle(u, v, e, prev_e):
    length = e[1]
    name = e[2]
    highway = e[3]
    bicycle = e[4]
    cycleway = e[5]

    cost = length

    if bicycle == 'no':
        return cost * 100

    if highway == 'cycleway' or cycleway == 'track':
        # Both of these indicate cycle tracks, which we consider the
        # baseline--everything else is more expensive.
        pass
    else:
        if highway == 'residential':
            cost *= 1.25
        elif highway == 'unclassified':
            cost *= 1.5
        elif highway in ('tertiary', 'tertiary_link'):
            cost *= 2
        elif highway in ('secondary', 'secondary_link'):
            cost *= 4
        elif highway == ('trunk', 'service'):
            cost *= 8
        elif highway in ('motorway', 'motorway_link'):
            cost *= 16
        elif highway in ('footway', 'living_street', 'path', 'pedestrian'):
            # Avoid pedestrians when possible
            cost *= 4
        else:
            # Be conservative and avoid unknown types
            cost *= 100

        if cycleway == 'lane':
            # Makes a residential street equivalent to a cycle track
            cost *= 0.8
        elif cycleway == 'shared_lane':
            cost *= 0.85
        elif bicycle == 'avoid':
            cost *= 4
        elif bicycle == 'designated' and cycleway != 'proposed':
            cost *= 0.9

    if prev_e and name != prev_e[2]:
        cost *= 1.25

    return cost


def bicycle_safer(u, v, e, prev_e):
    pass


def walk(u, v, e, prev_e):
    pass
