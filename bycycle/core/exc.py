class ByCycleError(Exception):

    """Root class for byCycle `Exception`s.

    The attributes of these exceptions are similar to WebOb's
    exceptions.

    Attributes
    ----------

    ``title``
        A short title for the error, as might be displayed in a heading.

    ``explanation``
        A brief description of the error.

    ``detail``
        Further details about the error (optional).

    """

    title = 'Error'
    explanation = 'An unspecified byCycle error occurred'
    detail = None

    def __init__(self, explanation=None, detail=None):
        if explanation is not None:
            self.explanation = explanation
        if detail is not None:
            self.detail = detail
        super().__init__(str(self))

    def __str__(self):
        parts = [self.title, self.explanation]
        if self.detail:
            parts.append(self.detail)
        return ' - '.join(parts)


class InputError(ByCycleError):

    title = 'Not Understood'
    explanation = 'That input was not understood'

    def __init__(self, errors, explanation=None):
        if isinstance(errors, str):
            errors = [errors]
        detail = '\n'.join(str(e) for e in errors)
        super().__init__(explanation, detail)
        self.errors = errors


class NotFoundError(ByCycleError):

    title = 'Not Found'
    explanation = 'Unable to find input'
