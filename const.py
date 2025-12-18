from datetime import timedelta

DOMAIN = "ubiant_hemis"

CONF_BASE_URL = "base_url"
CONF_BUILDING_ID = "building_id"
CONF_TOKEN = "token"

DEFAULT_SCAN_INTERVAL = timedelta(seconds=30)

PLATFORMS = ["sensor", "cover"]