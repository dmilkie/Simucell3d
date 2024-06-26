import sys
import time
import multiprocessing.pool
import signal
from functools import wraps

############################################################
# Timeout
############################################################

#The time out decorator contained in this file is a modification of the code found at:
#https://github.com/pnpnpn/timeout-decorator.git
#Instead of raising an exception when the time out is exceeded, a default value is returned.



#---------------------------------------------------------------------------------------------------
#This class are here to adapt the multiprocessing.pool class and allow the use of nested pools. This 
#is necessary to use the timeout decorator in a nested way.
class NoDaemonProcess(multiprocessing.Process):
    @property
    def daemon(self):
        return False

    @daemon.setter
    def daemon(self, value):
        pass


class NoDaemonContext(type(multiprocessing.get_context())):
    Process = NoDaemonProcess

# We sub-class multiprocessing.pool.Pool instead of multiprocessing.Pool
# because the latter is only a wrapper function, not a proper class.
class NestablePool(multiprocessing.pool.Pool):
    def __init__(self, *args, **kwargs):
        kwargs['context'] = NoDaemonContext()
        super(NestablePool, self).__init__(*args, **kwargs)
#---------------------------------------------------------------------------------------------------


#---------------------------------------------------------------------------------------------------
class TimeoutError(AssertionError):

    """Thrown when a timeout occurs in the `timeout` context manager."""

    def __init__(self, value="Timed Out"):
        self.value = value

    def __str__(self):
        return repr(self.value)


def _raise_exception(exception, exception_message):
    """ This function checks if a exception message is given.

    If there is no exception message, the default behaviour is maintained.
    If there is an exception message, the message is passed to the exception with the 'value' keyword.
    """
    if exception_message is None:
        raise exception()
    else:
        raise exception(exception_message)
#---------------------------------------------------------------------------------------------------




#---------------------------------------------------------------------------------------------------
def timeout(seconds=None,  default_value=None):
    """Add a timeout parameter to a function and return it.

    :param seconds: optional time limit in seconds or fractions of a second. If None is passed, no timeout is applied.
        This adds some flexibility to the usage: you can disable timing out depending on the settings.
    :type seconds: float
    :param use_signals: flag indicating whether signals should be used for timing function out or the multiprocessing
        When using multiprocessing, timeout granularity is limited to 10ths of a second.
    :type use_signals: bool
    :default_value: value to return if timeout occurs, the default value and the timeout exception are mutually exclusive

    :raises: TimeoutError if time limit is reached

    It is illegal to pass anything other than a function as the first
    parameter. The function is wrapped and returned to the caller.
    """

    def decorate(function):
        @wraps(function)
        def new_function(*args, **kwargs):
            timeout_wrapper = _Timeout(function, seconds, default_value)
            return timeout_wrapper(*args, **kwargs)
        return new_function
    return decorate
#---------------------------------------------------------------------------------------------------




#---------------------------------------------------------------------------------------------------
def _target(queue, function, *args, **kwargs):
    """Run a function with arguments and return output via a queue.

    This is a helper function for the Process created in _Timeout. It runs
    the function with positional arguments and keyword arguments and then
    returns the function's output by way of a queue. If an exception gets
    raised, it is returned to _Timeout to be raised by the value property.
    """
    try:
        queue.put((True, function(*args, **kwargs)))
    except:
        queue.put((False, sys.exc_info()[1]))
#---------------------------------------------------------------------------------------------------



#---------------------------------------------------------------------------------------------------
class _Timeout(object):

    """Wrap a function and add a timeout (limit) attribute to it.

    Instances of this class are automatically generated by the add_timeout
    function defined above. Wrapping a function allows asynchronous calls
    to be made and termination of execution after a timeout has passed.
    """
    def __init__(self, function, limit, default_value):
        """Initialize instance in preparation for being called."""
        self.__limit = limit
        self.__function = function
        self.__name__ = function.__name__
        self.__doc__ = function.__doc__
        self.__default_value = default_value
        self.__timeout_exceeded = False
        self.__timeout = time.time()
        self.__process = multiprocessing.Process()
        self.__queue = multiprocessing.Queue()

    def __call__(self, *args, **kwargs):
        """Execute the embedded function object asynchronously.

        The function given to the constructor is transparently called and
        requires that "ready" be intermittently polled. If and when it is
        True, the "value" property may then be checked for returned data.
        """
        self.__limit = kwargs.pop('timeout', self.__limit)
        self.__queue = multiprocessing.Queue(1)
        args = (self.__queue, self.__function) + args
        self.__process = multiprocessing.Process(target=_target,
                                                 args=args,
                                                 kwargs=kwargs)
        #self.__process.daemon = True
        self.__process.start()
        if self.__limit is not None:
            self.__timeout = self.__limit + time.time()
        while not self.ready:
            time.sleep(0.1)
        return self.value

    def cancel(self):
        """Terminate any possible execution of the embedded function."""
        if self.__process.is_alive():
            self.__process.terminate()
            

    @property
    def ready(self):
        """Read-only property indicating status of "value" property."""

        if self.__limit and self.__timeout < time.time():
            self.cancel()
            self.__timeout_exceeded = True
            return True
        return self.__queue.full() and not self.__queue.empty()

    @property
    def value(self):
        """Read-only property containing data returned from function."""
        if self.ready is True:
            #If the time out has been exceeded, return the default value
            if self.__timeout_exceeded:
                return self.__default_value
            else:
                flag, load = self.__queue.get()
                if flag:
                    return load
                raise load
#---------------------------------------------------------------------------------------------------




#---------------------------------------------------------------------------------------------------
max_simulation_time_sec = 10
failure_loss_value = 20
#---------------------------------------------------------------------------------------------------


#---------------------------------------------------------------------------------------------------
@timeout(seconds = max_simulation_time_sec, default_value=failure_loss_value)
def mytest():
    print("Start")
    for i in range(1,5):
        time.sleep(1)
        print("{} seconds have passed".format(i))
    return 1
#---------------------------------------------------------------------------------------------------



if __name__ == "__main__":

    test  = mytest()

    print(test)