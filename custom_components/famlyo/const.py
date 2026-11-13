"""Konstanten der Famlyo-Integration."""

from datetime import timedelta

DOMAIN = "famlyo"

DEFAULT_BASE_URL = "https://api.famlyo.de"
CONF_BASE_URL = "base_url"

# 30 s, mit ETag: eine unveraenderte Liste kostet den Server praktisch nichts.
# Nach jeder eigenen Aktion laedt die Integration ohnehin sofort nach.
SCAN_INTERVAL = timedelta(seconds=30)

SCOPE_SHOPPING_READ = "shopping:read"
SCOPE_SHOPPING_WRITE = "shopping:write"
SCOPE_INVENTORY_READ = "inventory:read"

# Dieselbe Grenze wie die Bestand-Kopfzeile der App (`MHD.soonThresholdDays`):
# „laeuft bald ab" heisst heute bis in drei Tagen.
EXPIRING_SOON_DAYS = 3

SERVICE_GET_STOCK = "get_stock"
ATTR_QUERY = "query"
