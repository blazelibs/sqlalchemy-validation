
def before_flush(f):
    """
        Use to decorate an instance method so that it is called before flush.
        This method will only be called on an instance if it is new or dirty.
        (i.e. it is in session.new or session.dirty).

        This decorated methods will be called before validation takes place.
    """
    f._sav_before_flush = 'yes'
    return f
