pytest-jsonverdict
==================

pytest-jsonverdict is a pytest-plugin which enables you to save some data of a test run to a .json-file.

It basically does two things:

* It counts how many of your tests were passed / failed /xpassed etc.
* It can add specific test outcomes to the JSON output.

## Output format and content


The content of the output file is as follows::

    {
        "start": "19.12.2017 15:21:08",
        "duration": 384.378414,
        "passed": 22,
        "failed": 7,
        "xpassed": 0,
        "xfailed": 16,
        "errors": 0,
        "rerun": null,
        "sum": 45,
        "extra": {
            "section1": {
                "node1": "passed",
                "node2": "xfailed"
            },
            "section2": {
                "node1": "failed",
                "node2": "error"
            },
        }
    }


| Field             | Type                                         | Description                                 |
| ----------------- | -------------------------------------------- | ------------------------------------------- |
| ``start``         | python date format: ``%d.%m.%Y %H:%M:%S``    | Test suite starting time                    |
| ``duration``      | float, seconds                               | Duration of the test run                    |
| ``passed``, ``failed``, ``xpassed``, ``xfailed``, ``errors`` | int | Nuber of tests ending in the corresponding state |
| ``rerun``         | int                                          | Unused, exists for compatibility reasons    |
| ``sum``           | int                                          | Sum of all tests                            |
| ``extra``         | map                                          | Collected ``@pytest.mark.json_extra`` sections (see plugin.py inline docs) |



The content of the extra-section is optional, depending if you use this feature or not, the extra structure will be
empty if not used.

