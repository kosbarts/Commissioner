class DefconError(Exception):

    _report = None

    def _set_report(self, value):
        self._report = value

    def _get_report(self):
        return self._report

    report = property(_get_report, _set_report)
