import binascii
import json
import logging
from logging import getLogger
from uuid import UUID

import requests
from requests import Response

log = getLogger(__name__)

import http.client as http_client

# enable intensive logging
if True or log.level == logging.DEBUG:
    http_client.HTTPConnection.debuglevel = 1
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True


class UbirchDevice(object):
    def __init__(self, auth=None, env=None) -> None:
        super().__init__()
        if auth is not None:
            self._auth = {'Authorization': auth}
        else:
            self._auth = {}

        if env is None:
            self.KEY_SERVICE = "http://localhost:8095/api/keyService/v1".format(env)
            self.AVATAR_SERVICE = "http://localhost:8096/api/avatarService/v1".format(env)
            self.CHAIN_SERVICE = "http://localhost:8097/api/v1/chainService".format(env)
            self.NOTARY_SERVICE = "https://localhost:8098/api/v1/notaryService".format(env)
        else:
            self.KEY_SERVICE = "https://key.{}.ubirch.com/api/keyService/v1".format(env)
            self.AVATAR_SERVICE = "https://api.ubirch.{}.ubirch.com/api/avatarService/v1".format(env)
            self.CHAIN_SERVICE = "https://api.ubirch.{}.ubirch.com/api/v1/chainService".format(env)
            self.NOTARY_SERVICE = "http://n.dev.ubirch.com:8080/v1/notaryService".format(env)

    def is_identity_registered(self, serial: str) -> bool:
        r = requests.get(self.KEY_SERVICE + "/pubkey/current/hardwareId/" + serial)
        log.info("{}: {}".format(r.status_code, r.content))
        return r.status_code == 200 and r.json()

    def register_identity(self, key_registration: bytes) -> Response:
        if key_registration.startswith(b'{'):
            log.debug(key_registration)
            return self._register_identity_json(json.loads(bytes.decode(key_registration)))
        else:
            return self._register_identity_mpack(key_registration)

    def _register_identity_json(self, key_registration: dict) -> Response:
        log.info("register device identity: {}".format(key_registration))
        r = requests.post(self.KEY_SERVICE + '/pubkey', json=key_registration)
        log.debug("{}: {}".format(r.status_code, r.content))
        return r

    def _register_identity_mpack(self, key_registration: bytes) -> Response:
        log.info("register device identity: {}".format(key_registration))
        r = requests.post(self.KEY_SERVICE + '/pubkey/mpack', data=key_registration,
                          headers={'Content-Type': 'application/octet-stream'})
        log.info("{}: {}".format(r.status_code, r.content))
        return r

    def device_exists(self, serial: str) -> bool:
        r = requests.get(self.AVATAR_SERVICE + '/device/' + serial)
        log.debug("{}: {}".format(r.status_code, r.content))
        return r.status_code == 200

    def create_device(self, device_info: dict) -> Response:
        r = requests.post(self.AVATAR_SERVICE + '/device',
                          json=device_info,
                          headers=self._auth)
        log.debug("{}: {}".format(r.status_code, r.content))
        return r

    def send(self, data: bytes) -> Response:
        if data.startswith(b'{'):
            return self._send_json(json.loads(bytes.decode(data)))
        else:
            return self._send_mpack(data)

    def anchor(self, data: bytes) -> UUID or None:
        if data.startswith(b'{'):
            raise Exception("unsupported data type: json")

        r = requests.post(self.NOTARY_SERVICE + '/notarize',
                          json={"data": binascii.hexlify(data[-64:]), "dataIsHash": True},
                          headers=self._auth)
        log.debug("{}: {}".format(r.status_code, r.content))
        if r.status_code == 200:
            return r.json()['hash']
        else:
            return None

    def _send_json(self, data: dict) -> Response:
        payload = str.encode(json.dumps(data, sort_keys=True, separators=(',', ':')))
        log.debug(json)
        r = requests.post(self.AVATAR_SERVICE + '/device/update',
                          headers={'Content-Type': 'application/json'},
                          data=payload)
        log.debug("{}: {}".format(r.status_code, r.content))
        return r

    def _send_mpack(self, data: bytes) -> Response:
        log.debug(data)
        r = requests.post(self.AVATAR_SERVICE + '/device/update/mpack', data=data)
        log.debug("{}: {}".format(r.status_code, r.content))
        return r
