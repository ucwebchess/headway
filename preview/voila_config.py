"""Voila configuration for the live app preview (viewing helper only).

Not part of the delivered package. Two things are configured here:

* bind to 0.0.0.0 so the platform can proxy the page;
* relax ``Content-Security-Policy: frame-ancestors`` to ``*`` so the page may be
  embedded in the preview iframe.  Everything else is left at its default.
"""


def _load(module):
    return module


c = get_config()  # noqa: F821 - provided by the voila/traitlets config loader
c.Voila.port = 8866
c.Voila.ip = "0.0.0.0"
c.Voila.open_browser = False
c.Voila.tornado_settings = {
    "headers": {"Content-Security-Policy": "frame-ancestors *"},
}
