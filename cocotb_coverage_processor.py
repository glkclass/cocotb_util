# CocoTB. Base TestBench class

import logging
from typing import Callable

from cocotb.log import SimLog
from cocotb_coverage.coverage import coverage_section, coverage_db

from cocotb_util.cocotb_transaction import Transaction
from cocotb_util.cocotb_coverage import CoverPoint, CoverCross

from cocotb_util.cocotb_util import timeout


class CoverProcessor(object):

    def __init__(
            self,
            name: str = "cocotb.coverage",
            report_cfg: dict = {'status': {}, 'final': {'bins': True}},
            **kwargs):

        self.log = SimLog(name)
        self.log.setLevel(logging.INFO)

        # list of callbacks to be called after CoverPoints calls at every sample
        self.callbacks = []

        # Create coverage_section decorator with cover items. To be used for coverage collection.
        self.define()

        # setup cover results reporting
        assert isinstance(report_cfg, dict)
        self.coverage_report_setup(report_cfg)

    def add_callback(self, func: Callable):
        """Add optional 'func' callback which will be called after all CoverItems sampled"""
        assert isinstance(func, Callable)
        self.callbacks.append(func)

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
            trx: Transaction,
            report_en: bool = True):
        """Function to collect coverage. It makes sense to call it somewhere."""
        assert isinstance(trx, Transaction)

        @self._coverage_section
        def foo(trx):
            self.log.debug('Collect coverage')
            pass

        foo(trx)
        if report_en:
            self.status_report()

    def coverage_report_setup(self, _coverage_report_cfg):
        """Check report config consistency with given coverage db"""
        cover_item_fields_supported = ['at_least', 'weight', 'new_hits', 'size', 'coverage', 'cover_percentage', 'detailed_coverage', 'covered_bins', 'bin_cnt']
        assert isinstance(_coverage_report_cfg, dict)
        self._coverage_report_cfg = _coverage_report_cfg
        status_cfg = self._coverage_report_cfg.get('status', None)
        if status_cfg is None:
            self.log.info('No coverage status reported.')
            self._coverage_report_cfg['status'] = {}
        else:
            assert isinstance(_coverage_report_cfg['status'], dict)
            for cov_item_name, cov_item_field_name in [item for item in status_cfg.items()]:
                assert isinstance(cov_item_name, str)
                assert type(cov_item_field_name) in [str, list]
                if isinstance(cov_item_field_name, str):
                    status_cfg[cov_item_name] = [cov_item_field_name]  # convert to list
                cov_item = coverage_db.get(cov_item_name, None)
                if cov_item is None:
                    self.log.warning(f'Wrong coverage_db item: {cov_item_name}.*')
                    del status_cfg[cov_item_name]
                    continue
                for cov_item_field_name in [item for item in status_cfg[cov_item_name]]:
                    field_base_name = cov_item_field_name.split(':')[0]
                    if field_base_name not in cover_item_fields_supported:
                        self.log.warning(f'Wrong coverage_db item field: {cov_item_name}.{field_base_name}')
                        status_cfg[cov_item_name].remove(cov_item_field_name)

    def status_report(self):
        """Function to report intermediate coverage status during the test. May be overridden."""
        for cov_item_name, cov_item_field_names in self._coverage_report_cfg['status'].items():
            for cov_item_field_name in cov_item_field_names:
                # handle 'fields' of dict type
                foo = cov_item_field_name.split(':')
                field_base_name = foo[0]
                cov_item_field_value = getattr(coverage_db[cov_item_name], field_base_name)
                if len(foo) > 1 and isinstance(cov_item_field_value, dict):
                    cov_item_field_value = cov_item_field_value.get(foo[1], cov_item_field_value)

                if isinstance(cov_item_field_value, float):
                    self.log.info(f"{cov_item_name}.{cov_item_field_name} = {cov_item_field_value:2.2f}")
                else:
                    self.log.info(f"{cov_item_name}.{cov_item_field_name} = {cov_item_field_value}")

    def final_report(self):
        """Function to report final coverage result at the end of the test. May be overridden"""
        self.log.info('Coverage final results')
        bins = self._coverage_report_cfg.get('final', {}).get('bins', True)
        assert isinstance(bins, bool)
        coverage_db.report_coverage(self.log.info, bins=bins)
