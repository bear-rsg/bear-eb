##
# Copyright 2018-2019 Ghent University
#
# This file is part of EasyBuild,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://www.vscentrum.be),
# Flemish Research Foundation (FWO) (http://www.fwo.be/en)
# and the Department of Economy, Science and Innovation (EWI) (http://www.ewi-vlaanderen.be/en).
#
# https://github.com/easybuilders/easybuild
#
# EasyBuild is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation v2.
#
# EasyBuild is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with EasyBuild.  If not, see <http://www.gnu.org/licenses/>.
##
"""
EasyBuild support for building and installing STAR-CCM+, implemented as an easyblock
"""
import glob
import os
import re
import tempfile

import easybuild.tools.environment as env
from easybuild.framework.easyblock import EasyBlock
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.config import build_option
from easybuild.tools.filetools import change_dir, read_file
from easybuild.tools.run import run_cmd


class EB_STAR_minus_CCM_plus_(EasyBlock):
    """Support for building/installing STAR-CCM+."""

    def __init__(self, *args, **kwargs):
        """Initialise STAR-CCM+ easyblock."""
        super(EB_STAR_minus_CCM_plus_, self).__init__(*args, **kwargs)
        self.starccm_subdir = None
        self.starview_subdir = None

    def configure_step(self):
        """No configuration procedure for STAR-CCM+."""
        pass

    def build_step(self):
        """No build procedure for STAR-CCM+."""
        pass

    def install_step(self):
        """Custom install procedure for STAR-CCM+."""
        cands = glob.glob("./STAR-CCM+%s_*.sh" % self.version)
        if len(cands) == 1:
            install_script = cands[0]

            env.setvar('CHECK_DISK_SPACE', 'OFF')
            env.setvar('IATEMPDIR', tempfile.mkdtemp())

            cmd = ' '.join([
                install_script,
                "-i silent",
                "-DINSTALLDIR=%s" % self.installdir,
                "-DINSTALLFLEX=false",
                "-DADDSYSTEMPATH=false",
                "-DPRODUCTEXCELLENCEPROGRAM=0",
            ])
            # Run the command, which may have a non-zero exit code (that we'll capture) even if it succeeds
            (_, ec) = run_cmd(cmd, simple=False, log_all=False, log_ok=False)
            if ec != 0:
                # The script may well have exited with non-fatal errors. We'll check.
                if self.starccm_subdir is None or self.starview_subdir is None:
                    self.find_starccm_subdirs()
                logfilepaths = glob.glob(os.path.join(
                    self.installdir,
                    self.starccm_subdir,
                    "STAR-CCM+%s*_InstallLog.log" % self.version))
                if len(logfilepaths) == 1:
                    logfilepath = logfilepaths[0]
                    self.log.debug("Checking output of logfile %s" % logfilepath)
                    logfile = read_file(logfilepath)
                    # First check output for unacceptable errors
                    regexp_fatal = re.compile(r"^(\d+)\sFatalErrors", re.M)
                    match_fatal = regexp_fatal.search(logfile)
                    if match_fatal:
                        if match_fatal.groups()[0] != '0':
                            fat_err_cnt = match_fatal.groups()[0]
                            raise EasyBuildError(
                                "%s fatal errors reported in logfile %s" % (fat_err_cnt, logfilepath)
                            )
                    # ... then check output for acceptable errors
                    regexp_nonfatal = re.compile(r"^(\d+)\sNonFatalErrors", re.M)
                    match_nonfatal = regexp_nonfatal.search(logfile)
                    if match_nonfatal:
                        err_cnt = match_nonfatal.groups()[0]
                        self.log.info(
                            "%s non-fatal errors reported in logfile %s" % (err_cnt, logfilepath)
                        )
                else:
                    raise EasyBuildError(
                        "Found no or multiple possible matches for STAR-CCM+ installation log file: %s", logfilepaths)
        elif not self.dry_run:
            raise EasyBuildError("Found no or multiple possible matches for STAR-CCM+ installation script: %s", cands)

    def find_starccm_subdirs(self):
        """Determine subdirectory of install directory in which STAR-CCM+ was installed."""
        cwd = change_dir(self.installdir)
        cands = glob.glob(os.path.join(self.version + '*', 'STAR-CCM+%s*' % self.version))
        if len(cands) == 1:
            self.starccm_subdir = cands[0]
            self.log.info("Found STAR-CCM+ subdirectory: %s", self.starccm_subdir)
            self.starview_subdir = os.path.join(os.path.dirname(self.starccm_subdir), 'STAR-View+%s' % self.version)
        elif self.dry_run or build_option('module_only'):
            # Provide fake string values if executing a dry-run or module-only build
            self.starccm_subdir = ''
            self.starview_subdir = ''
        else:
            raise EasyBuildError("Failed to determine the STAR-CCM+ subdirectory in %s: %s", self.installdir, cands)

        change_dir(cwd)

    def sanity_check_step(self):
        """Custom sanity check for STAR-CCM+."""
        if self.starccm_subdir is None or self.starview_subdir is None:
            self.find_starccm_subdirs()

        custom_paths = {
            'files': [os.path.join(self.installdir, self.starccm_subdir, 'star', 'bin', 'starccm+'),
                      os.path.join(self.installdir, self.starview_subdir, 'bin', 'starview+')],
            'dirs': [],
        }
        super(EB_STAR_minus_CCM_plus_, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_extra(self):
        """Extra statements specific to STAR-CCM+ to include in generated module file."""
        if self.starccm_subdir is None or self.starview_subdir is None:
            self.find_starccm_subdirs()

        txt = super(EB_STAR_minus_CCM_plus_, self).make_module_extra()

        bin_dirs = [
            os.path.join(self.starccm_subdir, 'star', 'bin'),
            os.path.join(self.starview_subdir, 'bin'),
        ]
        txt += self.module_generator.prepend_paths('PATH', bin_dirs)

        return txt
