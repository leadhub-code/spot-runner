class AppError (Exception):
    '''
    This exception is raised by application code and (hopefully) contains
    an useful error message.

    Therefore no traceback may be displayed on standard output.
    '''

    pass
