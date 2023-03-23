from datetime import datetime
import json
import random

import dateutil.parser as dp


def generate_query_path(url, params):
    entries = params.items()
    if not entries:
        return url

    paramsString = "&".join(
        "{key}={value}".format(key=x[0], value=x[1])
        for x in entries
        if x[1] is not None
    )
    if paramsString:
        return url + "?" + paramsString

    return url
