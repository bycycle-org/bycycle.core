from bycycle.core.exc import ByCycleError, NotFoundError


class RouteError(ByCycleError):

    title = 'Route Service Error'
    description = 'An unexpected error was encountered in the routing service'


class NoRouteError(RouteError, NotFoundError):

    title = 'Route Not Found'

    def __init__(self, start, end, explanation=None):
        description = 'Unable to find a route from {start} to {end}'
        description = description.format(start=start.address, end=end.address)
        super().__init__(description, explanation)
        self.start = start
        self.end = end


class EmptyGraphError(RouteError):

    title = 'Empty Routing Graph'
    description = 'The routing graph is empty (how is this possible?)'


class MultipleLookupResultsError(RouteError):

    title = 'Multiple Matches Found'
    description = (
        'Multiple results were found that match one or more input addresses')

    def __init__(self, choices=None, description=None, explanation=None):
        super().__init__(description, explanation)
        self.choices = choices
