try:
    from pkg_resources import get_distribution, DistributionNotFound
    __version__ = get_distribution("ttfautohint-py").version
except (ImportError, DistributionNotFound):
    # either pkg_resources is missing or package is not installed
    import warnings
    warnings.warn(
        "'ttfautohint-py' is missing the required distribution metadata. "
        "Please make sure it was installed correctly.", UserWarning,
        stacklevel=2)
    __version__ = "0.0.0"
