# Tai Sakuma <tai.sakuma@gmail.com>
import sys
import atexit
import threading
import multiprocessing
import contextlib

from .reporter import ProgressReporter
from .pickup import ProgressReportPickup
from .presentation.create import create_presentation
from . import detach

##__________________________________________________________________||
_presentation = None
_reporter = None
_pickup = None
_queue = None
_lock = threading.Lock()

##__________________________________________________________________||
def find_reporter():
    """returns the progress reporter

    This function is to be called in the main process of a
    multiprocessing program. The reporter should be registered in
    sub-processes with the function `register_reporter()`

    Returns
    -------
    object
        The progress reporter

    """

    global _lock
    global _reporter

    _lock.acquire()
    _start_pickup_if_necessary()
    _lock.release()

    return _reporter

##__________________________________________________________________||
def register_reporter(reporter):
    """registers a reporter

    This function is to be called in sub-processes of a
    multiprocessing program.

    Parameters
    ----------
    reporter : object
        The reporter obtained in the main process by the function
        `find_reporter()`


    Returns
    -------
    None

    """

    global _reporter
    _reporter = reporter

##__________________________________________________________________||
def flush():
    """flushes progress bars

    This function flushes all active progress bars. It returns when
    the progress bars finish updating.

    Returns
    -------
    None

    """
    global _lock
    _lock.acquire()
    _end_pickup()
    _lock.release()

atexit.register(flush)

##__________________________________________________________________||
@contextlib.contextmanager
def fetch_reporter():
    global _lock
    global _reporter

    _lock.acquire()
    started = _start_pickup_if_necessary()
    _lock.release()

    own_pickup = started and in_main_thread()

    try:
        yield _reporter
    finally:
        _lock.acquire()
        ## print('fetch_reporter _lock.acquire() 2')
        if detach.to_detach_pickup:
            own_pickup = False
        if own_pickup:
            _end_pickup()
        _lock.release()

def in_main_thread():
    try:
        return threading.current_thread() == threading.main_thread()
    except:
        # python 2
        return isinstance(threading.current_thread(), threading._MainThread)

##__________________________________________________________________||
def _start_pickup_if_necessary():
    global _reporter
    global _queue
    global _presentation
    global _pickup

    if _reporter is not None:
        return False

    if _queue is None:
        _queue = multiprocessing.Queue()

    _reporter = ProgressReporter(queue=_queue)
    _presentation = create_presentation()
    _pickup = ProgressReportPickup(_queue, _presentation)
    _pickup.daemon = True # this makes the functions
                          # registered at atexit called even
                          # if the pickup is still running

    _pickup.start()

    return True

##__________________________________________________________________||
def _end_pickup():
    global _queue
    global _presentation
    global _pickup
    global _reporter
    if _pickup:
        _queue.put(None)
        _pickup.join()
        _pickup = None
        _presentation = None
        detach.to_detach_pickup = False
    _reporter = None

##__________________________________________________________________||
