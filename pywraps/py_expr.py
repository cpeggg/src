# --------------------------------------------------------------------------
#<pycode(py_expr)>
try:
    import types
    import ctypes
    # Callback for IDC func callback (On Windows, we use stdcall)
    # typedef error_t idaapi idc_func_t(idc_value_t *argv,idc_value_t *r);
    _IDCFUNC_CB_T = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p)

    # A trampoline function that is called from idcfunc_t that will
    # call the Python callback with the argv and r properly serialized to python
    call_idc_func__ = ctypes.CFUNCTYPE(ctypes.c_long)(_ida_expr.py_get_call_idc_func())
except:
    def call_idc_func__(*args):
        warning("IDC extensions need ctypes library in order to work")
        return 0
    try:
        _IDCFUNC_CB_T = CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p)
    except:
        _IDCFUNC_CB_T = None


# --------------------------------------------------------------------------
EXTFUN_BASE  = 0x0001
"""requires open database"""
EXTFUN_NORET = 0x0002
"""does not return. the interpreter may clean up its state before calling it."""
EXTFUN_SAFE  = 0x0004
"""thread safe function. may be called"""

# --------------------------------------------------------------------------
class _IdcFunction(object):
    """
    Internal class that calls pyw_call_idc_func() with a context
    """
    def __init__(self, ctxptr):
        self.ctxptr = ctxptr
        # Take a reference to the ctypes callback
        # (note: this will create a circular reference)
        self.cb   = _IDCFUNC_CB_T(self)

    fp_ptr = property(lambda self: ctypes.cast(self.cb, ctypes.c_void_p).value)

    def __call__(self, args, res):
        return call_idc_func__(self.ctxptr, args, res)


# --------------------------------------------------------------------------
# Dictionary to remember IDC function names along with the context pointer
# retrieved by using the internal pyw_register_idc_func()
__IDC_FUNC_CTXS = {}

# --------------------------------------------------------------------------
def set_idc_func_ex(name, fp=None, args=(), flags=0):
    """
    Extends the IDC language by exposing a new IDC function that is backed up by a Python function
    This function also unregisters the IDC function if 'fp' was passed as None

    @param name: IDC function name to expose
    @param fp: Python callable that will receive the arguments and return a tuple.
               If this argument is None then the IDC function is unregistered
    @param args: Arguments. A tuple of idaapi.VT_XXX constants
    @param flags: IDC function flags. A combination of EXTFUN_XXX constants

    @return: Boolean.
    """
    global __IDC_FUNC_CTXS

    # Get the context
    f = __IDC_FUNC_CTXS.get(name, None)

    # Unregistering?
    if fp is None:
        # Not registered?
        if f is None:
            return False

        # Break circular reference
        del f.cb

        # Delete the name from the dictionary
        del __IDC_FUNC_CTXS[name]

        # Delete the context and unregister the function
        return _ida_expr.pyw_unregister_idc_func(f.ctxptr)

    # Registering a function that is already registered?
    if f is not None:
        # Unregister it first
        set_idc_func_ex(name, None)

    # Convert the tupple argument info to a string
    args = "".join([chr(x) for x in args])

    # Create a context
    ctxptr = _ida_expr.pyw_register_idc_func(name, args, fp)
    if ctxptr == 0:
        return False

    # Bind the context with the IdcFunc object
    f = _IdcFunction(ctxptr)

    # Remember the Python context
    __IDC_FUNC_CTXS[name] = f

    # Register IDC function with a callback
    return _ida_expr.py_set_idc_func_ex(
                name,
                f.fp_ptr,
                args,
                flags)

#</pycode(py_expr)>
