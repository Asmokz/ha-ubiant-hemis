from datetime import timedelta

DOMAIN = "ubiant_hemis"

CONF_EMAIL = "email"
CONF_PASSWORD = "password"

CONF_BASE_URL = "base_url"
CONF_BUILDING_ID = "building_id"
CONF_TOKEN = "token"

# Ubiant "hemisphere" API (auth + buildings infos)
AUTH_BASE_URL = "https://hemisphere.ubiant.com"

DEFAULT_SCAN_INTERVAL = timedelta(seconds=30)

PLATFORMS = ["sensor", "cover", "light", "climate"]
