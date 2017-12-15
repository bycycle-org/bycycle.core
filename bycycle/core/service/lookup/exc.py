from bycycle.core.exc import ByCycleError, NotFoundError


class LookupError(ByCycleError):

    pass


class NoResultError(LookupError, NotFoundError):

    title = 'Not Found'
    explanation = 'Could not find result'

    def __init__(self, term, detail=None):
        explanation = 'Could not find "{term}"'.format(term=term)
        super().__init__(explanation, detail)
        self.term = term


class MultipleLookupResultsError(LookupError):

    title = 'Multiple Matches Found'
    explanation = 'Multiple results were found'

    def __init__(self, choices=None, explanation=None, detail=None):
        super().__init__(explanation, detail)
        self.choices = choices
