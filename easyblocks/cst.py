##
# Copyright 2009-2020 Ghent University
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
EasyBuild support for building CST Studio Suite

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
@author: James Carpenter (University of Birmingham)
"""

from distutils.version import LooseVersion
import glob
import os
import re
import tempfile

import easybuild.tools.environment as env
from easybuild.easyblocks.generic.binary import Binary
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.filetools import remove_dir, write_file
from easybuild.tools.run import run_cmd


class EB_CST(Binary):
    """
    Support for installing CST Studio Suite
    """

    @staticmethod
    def extra_options(extra_vars=None):
        """Extra easyconfig parameters specific to CST Studio Suite easyblock."""
        extra_vars = {
            'sp_level': [None, "Service pack level to apply", CUSTOM]
        }
        return Binary.extra_options(extra_vars)

    def __init__(self, *args, **kwargs):
        """Initialize Binary-specific variables."""
        super(EB_CST, self).__init__(*args, **kwargs)

        # Setup for the Binary easyblock
        self.cfg['extract_sources'] = True

        self.replayfile = None

    def configure_step(self):
        """Configure CST installation."""
        self.replayfile = os.path.join(self.builddir, "installer.properties")
        replay_list = [
            "CHOSEN_FEATURE_LIST=Frontend",
            "CHOSEN_INSTALL_FEATURE_LIST=Frontend",
            "CHOSEN_INSTALL_SET=Custom",
            "LICENSE_TYPE=floating",
            "LICENSE_SERV_INPUT=\"%s@%s\"" % (self.cfg['license_server_port'], self.cfg['license_server']),
            "USER_INSTALL_DIR=%s" % self.installdir,
            "LICENSE_SERV_INPUT_1=%s@%s" % (self.cfg['license_server_port'], self.cfg['license_server']),
            "LICENSE_TYPE_1=",
            "LICENSE_TYPE_2=Point to an existing CST license server system",
            "LICENSE_TYPE_BOOLEAN_1=0",
            "LICENSE_TYPE_BOOLEAN_2=1",
        ]
        if LooseVersion(self.version) >= LooseVersion('2022'):
            replay_list.extend([
                "LICENSE_MODE_1=",
                "LICENSE_MODE_2=Flexnet-based licensing",
            ])
        write_file(self.replayfile, '\n'.join(replay_list))

    def install_step(self):
        """Copy all files in build directory to the install directory"""

        # CST installer outputs into /tmp so we'll send the content elsewhere and tidy later
        tmpdir = tempfile.mkdtemp()
        env.setvar('IATEMPDIR', tmpdir)
        self.log.debug("Setting temp to: %s" % tmpdir)

        cmdlist = [
            '%s/SIMULIA_CST_Studio_Suite.Linux64/install.sh' % self.builddir,
            '--nogui',
            '--force-system-java',
            '--no-pkg-check',
            '--replay %s' % self.replayfile,
        ]

        cmd = ' '.join(cmdlist)
        # Run the command but ignore the exit code which will likely be non-zero
        (out, _) = run_cmd(cmd, simple=False, log_all=False, log_ok=False)
        self.log.debug("Output from install.sh:\n\n%s" % out)
        # Search for "*** Installation successful ***" in the output text
        if not re.search("Installation successful", out) and not self.dry_run:
            raise EasyBuildError("CST install.sh command failed with output:\n\n%s" % out)

        # Next, run the service-pack update, if available:
        if self.cfg['sp_level']:
            glob_string = "%s/CST_S2*%s*.sup" % (self.builddir, self.cfg['sp_level'])
            print(glob_string)
            # raise SystemExit()
            self.log.debug("Globbing for sup file using the following: %s" % glob_string)
            sp_cands = glob.glob(glob_string)
            if len(sp_cands) == 1:
                sp_filepath = sp_cands[0]
                cmd = "%s/update_with_supfile %s" % (self.installdir, sp_filepath)
                (out, _) = run_cmd(cmd, simple=False, log_all=False, log_ok=False)
                self.log.debug("Output from supplementary update:\n\n%s" % out)
                # Search for "Update completed successfully" in the output text
                if not re.search("Update completed successfully", out) and not self.dry_run:
                    raise EasyBuildError("CST update failed with output:\n\n%s" % out)
            elif not self.dry_run:
                raise EasyBuildError("Unable to locate definitive service pack update file: %s" % sp_cands)

        remove_dir(tmpdir)

    def sanity_check_step(self):
        """Custom sanity check for CST."""

        custom_paths = {
            'files': [os.path.join(".", x) for x in ["cst_design_environment", "cst_design_environment_gui"]],
            'dirs': ["Examples", "Library", "LinuxAMD64"],
        }

        super(EB_CST, self).sanity_check_step(custom_paths=custom_paths)
