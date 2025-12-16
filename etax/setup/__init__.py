# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

from etax.setup.install import after_install, before_uninstall, after_uninstall
from etax.setup.indexes import setup_indexes

__all__ = ["after_install", "before_uninstall", "after_uninstall", "setup_indexes"]
