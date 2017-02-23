from datetime import datetime

# the constants and functions below refer to
# https://bugzilla.readthedocs.io/en/5.0/api/core/v1/general.html#common-data-types
BUGZILLA_DATE_FORMAT = "%Y-%m-%d"
BUGZILLA_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

def parse_bugzilla_datetime(string):
    return datetime.strptime(string, BUGZILLA_DATETIME_FORMAT)

def parse_bugzilla_date(string):
    return datetime.strptime(string, BUGZILLA_DATE_FORMAT)

def encode_bugzilla_datetime(dt):
    if dt is None:
        return None
    
    return dt.strftime(BUGZILLA_DATETIME_FORMAT)

def encode_bugzilla_date(dt):
    if dt is None:
        return None
    
    return dt.strftime(BUGZILLA_DATE_FORMAT)