from authorizer import Signer
import json
import os
import time
import requests
from urllib.parse import urljoin

# Choose environment
BASE_URL = "https://api.acquiring.averspay.kg"        # prod
# BASE_URL = "https://beta.api.acquiring.averspay.kg"  # beta

HOST = "api.acquiring.averspay.kg"                     # must match BASE_URL host exactly
# HOST = "beta.api.acquiring.averspay.kg"

API_KEY = os.environ["FINIK_API_KEY"]                  # from Finik
PRIVATE_KEY_PEM = os.environ["FINIK_PRIVATE_PEM"]      # contents of finik_private.pem

timestamp = str(int(time.time() * 1000))               # UNIX ms

body = {
    "Amount": 100,
    "CardType": "FINIK_QR",
    "PaymentId": "00000000-0000-0000-0000-000000000000",  # use a real UUID
    "RedirectUrl": "https://example.com/success",
    "Data": {
        "accountId": "your-account-id",
        "merchantCategoryCode": "0742",
        "name_en": "your-qr-name"
    }
}

request_data = {
    "http_method": "POST",
    "path": "/v1/payment",
    "headers": {
        "Host": HOST,                     # must equal BASE_URL's host
        "x-api-key": API_KEY,
        "x-api-timestamp": timestamp,
    },
    # If you have queries, set a dict here; signer will encode/sort them
    "query_string_parameters": None,
    "body": body,                         # plain dict; signer will canonicalize/JSON-stringify
}

# Produce Base64 RSA-SHA256 signature
signature = Signer(**request_data).sign(PRIVATE_KEY_PEM)

# Send the request
url = urljoin(BASE_URL, request_data["path"])
resp = requests.post(
    url,
    headers={
        "content-type": "application/json",
        "x-api-key": API_KEY,
        "x-api-timestamp": timestamp,
        "signature": signature,
    },
    data=json.dumps(body, separators=(",", ":")),  # compact JSON (no spaces)
    # prevent auto-follow to get payment link in the header.location:
    allow_redirects=False,
)

if resp.status_code == 201:
    print("Created:", resp.json())  # -> { paymentId, paymentUrl, status }
elif resp.status_code in (301, 302, 303, 307, 308):
    print("Redirect to:", resp.headers.get("Location"))
else:
    print(resp.status_code, resp.text)