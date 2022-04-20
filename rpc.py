import Pyro5.api as pyro_api

PYROD_PORT = 5000


def get_remote_object(id, ip):
    return pyro_api.Proxy(f"PYRO:{id}@{ip}:{PYROD_PORT}")
