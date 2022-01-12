# CocoTB. Base TestBench class

import logging
from functools import wraps
import importlib

from cocotb.log import SimLog

cocotb_coverage = importlib.import_module('cocotb-coverage.cocotb_coverage.coverage')
coverage_db = cocotb_coverage.coverage_db
CocoTBCoverPoint = cocotb_coverage.CoverPoint
CocoTBCoverCross = cocotb_coverage.CoverCross

class CoverPoint(CocoTBCoverPoint):
    def __new__(cls, name, *args, **kwargs):
        if name in coverage_db:
            return coverage_db[name]
        else:
            return super().__new__(cls, name)

    def __init__(self, name, *args, inj=False, **kwargs):
        if name not in coverage_db:
            super().__init__(name, *args, inj=inj, **kwargs)
            if getattr(self, 'log', None) is None:
                self.log = SimLog(f"cocotb.{name}")
                self.log.setLevel(logging.INFO)

            self.log.debug(f'Create CoverPoint: {name}')
            self._covered_bins = []  # to fill with covered bins

    def __call__(self, f):
        """Collect coverage decorator. Call super func + custom func"""
        super_call = super().__call__(f)

        @wraps(f)
        def _wrapped_function(*cb_args, **cb_kwargs):
            self.log.debug(f'Collect coverage for {self._name}')
            foo = super_call(*cb_args, **cb_kwargs)
            self.update_covered_bins()
            return foo
        return _wrapped_function

    def update_covered_bins(self):
        """Update list of covered bins"""
        for hit in self.new_hits:
            if self.detailed_coverage[hit] == self._at_least:
                self._covered_bins.append(hit)
                self.log.debug(f"Covered bins: {self._covered_bins}")

    @property
    def covered_bins(self):
        try:
            return self._covered_bins
        except AttributeError:
            return None

    @property
    def bin_cnt(self):
        try:
            return self._bin_cnt
        except AttributeError:
            return None


class CoverCross(CocoTBCoverCross):

    def __new__(cls, name, *args, **kwargs):
        if name in coverage_db:
            return coverage_db[name]
        else:
            return super().__new__(cls, name)

    def __init__(self, name, *args, **kwargs):
        if name not in coverage_db:
            super().__init__(name, *args, **kwargs)
            if getattr(self, 'log', None) is None:
                self.log = SimLog(f"cocotb.{name}")
                self.log.setLevel(logging.INFO)
            self.log.debug(f'Create CoverCross: {name}')

            # Initialize data to update 'covered cp bins' for every ccp dimension
            self._covered_bins = {}
            self._bin_cnt = {}
            for cp_name in self._items:
                self._covered_bins[cp_name] = []  # to fill with covered bins
                self._bin_cnt[cp_name] = {}  # for every cp prepare dict with {cp_bin: num_child_ccp_bins}
            # for every cp bin calc num of descendant ccp bins
            for ccp_bin in self.detailed_coverage:
                for i, cp_bin in enumerate(ccp_bin):
                    cp_name = self._items[i]
                    try:
                        self._bin_cnt[cp_name][cp_bin] += 1
                    except KeyError:
                        self._bin_cnt[cp_name][cp_bin] = 1

            # remove rest of 'ignore bins' from _hits which components are defined by list of cv bins.
            # 'ignore bins' which components were defined by cp bins or None (wildcard *) were already removed in super().__init__()
            ign_bins = kwargs.get('ign_bins', [])
            len_hits_former = len(self._hits)
            for x_bin in list(self._hits.keys()):
                for ignore_bins in ign_bins:
                    assert len(ignore_bins) == len(x_bin), f"Length({len(ignore_bins)}) of ignore bin({ignore_bins}) doesn't match to length({len(x_bin)}) of cross one{x_bin}"
                    remove = True
                    for ii in range(0, len(x_bin)):
                        if isinstance(ignore_bins[ii], (list, tuple)):
                            if (x_bin[ii] not in ignore_bins[ii]):
                                remove = False
                        else:
                            if (x_bin[ii] != ignore_bins[ii]):
                                remove = False
                    if remove and (x_bin in self._hits):
                        del self._hits[x_bin]
                        self.log.debug(f"Remove ignore bin: {x_bin}")
            # compensate former size update
            self._parent._update_size(-self._weight * len_hits_former)
            self.log.debug(f"Compensate former size: {-self._weight * len_hits_former}")
            # Update latter size
            self._size = self._weight * len(self._hits)
            self._parent._update_size(self._size)
            self.log.debug(f"Update latter size: {self._size}")

    def __call__(self, f):
        super_call = super().__call__(f)

        @wraps(f)
        def _wrapped_function(*cb_args, **cb_kwargs):
            self.log.debug(f'Collect coverage for {self._name}')
            foo = super_call(*cb_args, **cb_kwargs)
            self.update_covered_bins()
            return foo
        return _wrapped_function

    def update_covered_bins(self):
        """Update list of covered cp bins for every ccp dimension"""
        # Update 'covered bins' for every ccp dimension
        for hit in self.new_hits:
            if self.detailed_coverage[hit] == self._at_least:
                for i, cp_bin in enumerate(hit):
                    cp_name = self._items[i]
                    self._bin_cnt[cp_name][cp_bin] -= 1
                    if self._bin_cnt[cp_name][cp_bin] == 0:
                        self._covered_bins[cp_name].append(cp_bin)
                        self.log.warning(f"Covered bins: {cp_name} - {self._covered_bins[cp_name]}")

    @property
    def covered_bins(self):
        try:
            return self._covered_bins
        except AttributeError:
            return None

    @property
    def bin_cnt(self):
        try:
            return self._bin_cnt
        except AttributeError:
            return None
