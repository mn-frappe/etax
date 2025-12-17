# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

from etax.setup.indexes import setup_indexes
from etax.setup.install import after_install, after_uninstall, before_uninstall

__all__ = ["after_install", "after_uninstall", "before_uninstall", "setup_indexes"]
