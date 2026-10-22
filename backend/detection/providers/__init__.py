"""Built-in plug-ins. Importing this package registers them.

Add your own here (one module per plug-in, imported below) or in your own package, loaded with
DETECTION_PLUGINS=your.module. See docs/plugins.md.
"""

from . import example, http, none  # noqa: F401
