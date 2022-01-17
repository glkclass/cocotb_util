# CocoTB util
import os
import time
import logging
import numpy
from functools import wraps

from cocotb.clock import Clock
from cocotb.triggers import Timer
from cocotb.handle import SimHandleBase
from cocotb.result import TestSuccess

# from cocotb_util.cocotb_testbench import TestBench

log = logging.getLogger(__name__)
# log.addHandler(logging.StreamHandler())
log.setLevel(logging.INFO)


def init_random_seed():
    """Initialize 'numpy' lib seed. 'random' lib seed is initialized inside 'cocotb' lib"""
    random_seed = os.environ.get('RANDOM_SEED', None)
    if random_seed is not None:
        numpy.random.seed(int(random_seed))


def set_starttime():
    """Store test start time (int number of seconds) to the env"""
    os.environ['COCOTB_START_TIME_SECONDS'] = str(int(time.time()))


def static_vars(**kwargs):
    """Static variable emulate"""
    def decorate(func):
        for k in kwargs:
            setattr(func, k, kwargs[k])
        return func
    return decorate


def timeout(func):
    """ Timeout decorator.
        1. Print test time to log every minite
        2. Stop test when 'timeout' achieved
        (appropriate env vars should be set up at the 'test_start_point')"""
    cnt = 0
    duration_hours = os.environ.get('COCOTB_TIMEOUT_HOURS', None)
    start_time_sec = os.environ.get('COCOTB_START_TIME_SECONDS', None)

    def inner(*args, **kwargs):
        nonlocal cnt
        cnt += 1
        if cnt == 10:
            cnt = 0
            if start_time_sec is not None:
                run_time_sec = int(time.time()) - int(start_time_sec)
                # report current test time
                hours = int(run_time_sec / 3600)
                mins = int((run_time_sec % 3600) / 60)
                log.info('')
                if hours == 0:
                    log.info(f'Run time: {mins}m')
                else:
                    log.info(f'Run time: {hours}h {mins}m')
                log.info('')
                # terminate test if test time out
                if duration_hours is not None:
                    if run_time_sec > int(duration_hours) * 3600:
                        log.warning(f'Test timeout achieved. Run time: {run_time_sec}')
                        # report final coverage after termination if use with TestBench() member
                        if len(args) > 0 and getattr(args[0], 'report_coverage_final', None) is not None:
                            args[0].report_coverage_final()
                        raise TestSuccess
        return func(*args, **kwargs)
    return inner


def clk_625MHz(clk_in):
    return Clock(clk_in, 1.6, units="ns").start()


def clk_1GHz(clk_in):
    return Clock(clk_in, 1, units="ns").start()


async def reset(reset_n, duration_ns):
    reset_n.value = 0
    await Timer(duration_ns, units="ns")
    reset_n.value = 1
    reset_n._log.debug("Reset complete")


def assign_probe_str(probe: SimHandleBase, msg: str):
    """Assign string msg to packed logic/bit vector. Use for debug to display python string msg in waveforms"""
    if not isinstance(probe, SimHandleBase):
        return
    msg = str.encode(msg)  # to byte arr
    n = min(len(msg), int(len(probe) / 8))  # min between msg length and buffer size
    probe.setimmediatevalue(0)  # cleanup
    for i in range(n):
        for j in range(8):
            probe[8 * (n - 1 - i) + j].value = (msg[i] >> j) & 1


def assign_probe_int(probe: SimHandleBase, val: int):
    """Assign int val to int var. Use for debug to display python int in waveforms"""
    if not isinstance(probe, SimHandleBase):
        return
    probe.value = val
