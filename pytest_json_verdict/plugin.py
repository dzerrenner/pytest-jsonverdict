import json
import os

import pytest

from datetime import datetime


def pytest_addoption(parser):
    """
    Adds an parameter to the commandline-parameters of pytest which
    can be used to activate the plugin and specify the output filename.

    Example:
        `pytest --json=/path/to/output.json`

    """
    group = parser.getgroup('reporting')
    group.addoption('--json', action='store', dest='jsonpath',
                    metavar='path', default=None,
                    help='create json verdict file at given path.')


def pytest_configure(config):
    """
    Creates the JSONReport-Object and binds it to the pytest configuration.
    """
    jsonpath = config.option.jsonpath
    # prevent opening path on slave nodes (xdist)
    if jsonpath and not hasattr(config, 'slaveinput'):
        config._json = JSONReport(jsonpath, config)
        config.pluginmanager.register(config._json)


def pytest_unconfigure(config):
    """
    Removes the JSONReport object from the pytest configuration
    """
    json_plugin = getattr(config, '_json', None)
    if json_plugin:
        del config._json
        config.pluginmanager.unregister(json_plugin)


class JSONReport(object):
    def __init__(self, jsonfile, config):
        jsonfile = os.path.expanduser(os.path.expandvars(jsonfile))
        self.jsonfile = os.path.abspath(jsonfile)
        self.config = config
        self.errors = self.failed = 0
        self.passed = self.skipped = 0
        self.xfailed = self.xpassed = 0
        has_rerun = config.pluginmanager.hasplugin('rerunfailures')
        self.rerun = 0 if has_rerun else None
        self.extra = {}

    def append_passed(self, report):
        if report.when == 'call':
            if hasattr(report, "wasxfail"):
                self.xpassed += 1
            else:
                self.passed += 1

    def append_failed(self, report):
        if report.when == "call":
            if hasattr(report, "wasxfail"):
                # pytest < 3.0 marked xpasses as failures
                self.xpassed += 1
            else:
                self.failed += 1
        else:
            self.errors += 1

    def append_skipped(self, report):
        if hasattr(report, "wasxfail"):
            self.xfailed += 1
        else:
            self.skipped += 1

    def append_other(self, report):
        # For now, the only "other" the plugin give support is rerun
        self.rerun += 1

    def pytest_runtest_logreport(self, report):
        if report.passed:
            self.append_passed(report)
        elif report.failed:
            self.append_failed(report)
        elif report.skipped:
            self.append_skipped(report)
        else:
            self.append_other(report)

    @pytest.mark.hookwrapper
    def pytest_runtest_makereport(self, item, call):
        """
        This hook will be executed while pytest is generation an Report-Entry for the result list. It will take pytests
        results and add them to the json data if they were marked accordingly. All extra data will be stored in the top
        level element named "extra" in the output.

        The marker has the following syntax:
        `@pytest.mark.json_extra(key=<key>, mapping=<mapping>)`

        The key parameter is the name of the structure where the extra values are stored.



        Examples:
        - Basic usage:
            `@pytest.mark.json_extra(key="myresults")`

            This will result in the following output structure:

            ```
            {
                "start": ...
                "duration": ...
                ...
                "extra": {
                    "myresults": {
                        "tests/test_package/test_file.py::Test_class::()::test_method[test_ids]": "passed"
                    }
                }
            }
            ```

        - Mapping node-ids to simpler names:
            If you want the key in your results structure in a more readable form, you can specify a mapping from
            node-ids to human readable names:
            `@pytest.mark.json_extra(key="myresults", mapping=mymapping)`

            With mymapping being either a dictionary which is used to lookup the node id (as key in the dict) and using
            the vallue mapped by the dict:

            mymapping = {
                "tests/test_package/test_file.py::Test_class::()::test_method[test_ids]": "myspecialtestfunction",
            }

            This will result in an output structure like this

            ```
            {
                "start": ...
                "duration": ...
                ...
                "extra": {
                    "myresults": {
                        "myspecialtestfunction": "passed"
                    }
                }
            }
            ```

            Or you can use a callable (i.e. a python function) which will then be called with the nodeid as the single
            parameter. The return value of the function is then used as key in the jeson structure:

            def mymapping(value):
                return value.upper()

            ```
            {
                "start": ...
                "duration": ...
                ...
                "extra": {
                    "myresults": {
                        "TESTS/TEST_PACKAGE/TEST_FILE.PY::TEST_CLASS::()::TEST_METHOD[TEST_IDS]": "passed"
                    }
                }
            }
            ```

        :param item: :class: `_pytest.main.Item` Object containing Information about the test
        :param call: Call marker, can be either "setup", "call" or "teardown". Only call makes sense for this hook impl.
        :return:
        """
        outcome = yield
        report = outcome.get_result()
        if call.when == "call":
            json_marker = item.get_marker("json_extra")
            if json_marker:
                key = json_marker.kwargs.get("key")
                if key not in self.extra:
                    self.extra[key] = {}
                mapping = json_marker.kwargs.get("mapping", None)
                if not mapping:
                    self.extra[key][report.nodeid] = report.outcome
                    return
                # use mapping as dict or call function
                if callable(mapping):
                    try:
                        self.extra[key][mapping(report.nodeid)] = report.outcome
                    finally:
                        return
                elif isinstance(mapping, dict):
                    try:
                        self.extra[key][mapping[report.nodeid]] = report.outcome
                    finally:
                        return
                else:
                    raise AttributeError("parameter mapping of json_extra marker has to be callable or subclass of dict"
                                         " (or None).")

    def pytest_sessionstart(self, session):
        self.start_time = datetime.now()

    def pytest_sessionfinish(self, session):
        self.duration = datetime.now() - self.start_time
        data = {
            "start": self.start_time.strftime("%d.%m.%Y %H:%M:%S"),
            "duration": self.duration.total_seconds(),
            "passed": self.passed,
            "failed": self.failed,
            "xpassed": self.xpassed,
            "xfailed": self.xfailed,
            "errors": self.errors,
            "rerun": self.rerun,
            "sum": self.passed + self.failed + self.xpassed + self.xfailed + self.errors,
            "extra": self.extra,
        }

        dir_name = os.path.dirname(self.jsonfile)

        if not os.path.exists(dir_name):
            os.makedirs(dir_name)

        with open(self.jsonfile, 'w', encoding='utf-8') as f:
            json.dump(data, f)

    def pytest_terminal_summary(self, terminalreporter):
        terminalreporter.write_sep('-', f"generated json file: {self.jsonfile}")
