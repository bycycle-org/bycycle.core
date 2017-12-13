from bycycle.core.exc import ByCycleError


class LookupError(ByCycleError):

    pass


class MultipleLookupResultsError(LookupError):

    title = 'Multiple Matches Found'
    explanation = 'Multiple results were found'

    def __init__(self, choices=None, explanation=None, detail=None):
        super().__init__(explanation, detail)
        self.choices = choices
