#!/usr/bin/python3
"""Launcher installed as /usr/bin/tuxoflood by the Debian package."""
import sys

sys.path.insert(0, "/usr/share/tuxoflood")

from tuxoflood.app import main  # noqa: E402

sys.exit(main())
