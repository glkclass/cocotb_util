# CocoTB. Base TestBench class

import importlib

import logging
from typing import Callable

from cocotb.log import SimLog

cocotb_coverage = importlib.import_module('cocotb-coverage.cocotb_coverage.coverage')
coverage_db = cocotb_coverage.coverage_db
coverage_section = cocotb_coverage.coverage_section

from cocotb_util.cocotb_transaction import Transaction
# from cocotb_util.cocotb_coverage import CoverPoint, CoverCross

from cocotb_util.cocotb_util import timeout


class CoverProcessor(object):

    def __init__(
            self,
            name: str = "cocotb.coverage",
            trx: Transaction = None,
            report_cfg: dict = {'status': {}, 'final': {'bins': True}},
            **kwargs):

        self.log = SimLog(name)
        self.log.setLevel(logging.INFO)

        # list of callbacks to be called after CoverPoints calls at every sample
        self.callbacks = []
        self.status_report_callback = None
        self.final_report_callback = None

        self.trx = trx  # Transaction class handle

        # Create coverage_section decorator with cover items. To be used for coverage collection.
        self.define()

    def add_callback(self, func: Callable):
        """Add optional 'func' callback which will be called after all CoverItems sampled"""
        assert isinstance(func, Callable)
        self.callbacks.append(func)

    def add_status_report_callback(self, func: Callable):
        """Add optional 'func' callback which will be called instead of standart staus report"""
        assert isinstance(func, Callable)
        self.status_report_callback = func

    def add_final_report_callback(self, func: Callable):
        """Add optional 'func' callback which will be called instead of standart staus report"""
        assert isinstance(func, Callable)
        self.final_report_callback = func

    def _callback_dec(self, func):
        """ 'Coverage post process' decorator. Call list of registered callbacks after all the CoverItems sampled.
        """
        def inner(*args, **kwargs):
            for callback_func in self.callbacks:
                callback_func(*args, **kwargs)
            return func(*args, **kwargs)
        return inner

    def add_cover_items(self, *args):
        """Schedule Cover items (Point & Cross) and 'callback' calls"""
        self._coverage_section = coverage_section(*args, self._callback_dec)

    def define(self):
        """Create coverage collector decorator using self.add_cover_items(CoverPoint, CoverCross, ...). To be overridden."""
        self.log.error('Not implemented')

    @timeout
    def collect(
            self,
            trx: Transaction):
        """Function to collect coverage. It makes sense to call it somewhere."""
        assert isinstance(trx, Transaction)

        @self._coverage_section
        def foo(trx):
            self.log.debug('Collect coverage')
            pass

        foo(trx)
        self.status_report()

    def status_report(self):
        """Function to report intermediate coverage status during the test."""
        if self.status_report_callback is not None:
            self.status_report_callback()
        else:
            coverage_db.report_coverage(self.log.info, bins=False)

    def final_report(self):
        """Function to report final coverage result at the end of the test"""
        self.log.info('Coverage final results')
        if self.final_report_callback is not None:
            self.final_report_callback()
        else:
            coverage_db.report_coverage(self.log.info, bins=True)
