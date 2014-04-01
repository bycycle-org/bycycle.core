class ByCycleError(Exception):

    """Root class for byCycle `Exception`s.

    Attributes
    ----------

    ``title``
        A short title for the error, as might be displayed in a heading.

    ``description``
        A brief description of the error.

    ``explanation``
        A more long winded explanation of the error.

    """

    title = 'Error'
    description = 'An unspecified byCycle error occurred'
    explanation = None

    def __init__(self, description=None, explanation=None):
        if description is not None:
            self.description = description
        if explanation is not None:
            self.explanation = explanation
        super().__init__(str(self))

    def __str__(self):
        return str(': '.join((self.title, self.description)))


class InputError(ByCycleError):

    title = 'Not Understood'
    description = 'That input was not understood'

    def __init__(self, errors, explanation=None):
        if isinstance(errors, str):
            errors = [errors]
        description = '\n'.join(str(e) for e in errors)
        super().__init__(description, explanation)
        self.errors = errors


class NotFoundError(ByCycleError):

    title = 'Not Found'
    description = 'Not Found'
