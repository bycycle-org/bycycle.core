from bycycle.core.exc import ByCycleError, NotFoundError


class RouteError(ByCycleError):

    title = 'Route Service Error'
    explanation = 'An unexpected error was encountered in the routing service'


class NoRouteError(RouteError, NotFoundError):

    title = 'Route Not Found'
    explanation = 'Unable to find route'

    def __init__(self, start, end, detail=None):
        explanation = 'Unable to find a route from "{start}" to "{end}"'
        explanation = explanation.format(start=start.name, end=end.name)
        super().__init__(explanation, detail)
        self.start = start
        self.end = end


class EmptyGraphError(RouteError):

    title = 'Empty Routing Graph'
    explanation = 'The routing graph is empty (how is this possible?)'


class MultipleRouteLookupResultsError(RouteError):

    title = 'Multiple Matches Found'
    explanation = 'Multiple results were found that match one or more input addresses'

    def __init__(self, choices=None, explanation=None, detail=None):
        super().__init__(explanation, detail)
        self.choices = choices
