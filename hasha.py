import hashlib

BIT_NUM = 256


def hash(ip: str) -> int:
    # id_bytes = hashlib.sha256(ip.encode()).digest()
    # return int.from_bytes(id_bytes, byteorder="little")
    # # The following line is for debugging purposes only
    return int(ip.split(".")[-1])
