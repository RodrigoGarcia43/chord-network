import inspect  # noqa: F401
import random
import sys
import threading
import time

import Pyro5.api as pyro_api

import hasha
import rpc

PING_PORT = 5001


class FingerEntry:
    def __init__(self):
        self.start = 0
        self.interval = 0
        self.node = 0


@pyro_api.expose
class ChordNode:
    def __init__(self, ip, id, bits):
        self.ip = ip
        self.id = id
        self.bits = bits
        self.joined = False

        self.finger = [FingerEntry() for _ in range(self.bits + 1)]
        for i in range(1, self.bits + 1):
            self.finger[i].start = (self.id + 2 ** (i - 1)) % (2 ** self.bits)

        self._predecessor = self.id

        self._id_ip = {self.id: self.ip}

    def get_id_ip(self, id):
        return self._id_ip[id]

    def set_id_ip(self, id, ip):
        self._id_ip[id] = ip

    def get_remote_object(self, id):
        return rpc.get_remote_object(id, self.get_id_ip(id))

    @property
    def predecessor(self):
        return self._predecessor

    @predecessor.setter
    def predecessor(self, value):
        self._predecessor = value

    def ask_predecessor(self, node_id):
        # print(inspect.currentframe().f_code.co_name)
        with self.get_remote_object(node_id) as remote_node:
            pred = remote_node.predecessor
            self.set_id_ip(pred, remote_node.get_id_ip(pred))
            return pred

    def ask_set_predecessor(self, node_id, pred_id):
        # print(inspect.currentframe().f_code.co_name)
        with self.get_remote_object(node_id) as remote_node:
            remote_node.predecessor = pred_id
            remote_node.set_id_ip(pred_id, self.ip)

    @property
    def successor(self):
        return self.finger[1].node

    def ask_successor(self, node_id):
        # print(inspect.currentframe().f_code.co_name)
        if node_id == self.id:
            return self.successor

        with self.get_remote_object(node_id) as remote_node:
            succ = remote_node.successor
            self.set_id_ip(succ, remote_node.get_id_ip(succ))
            return succ

    def find_successor(self, id):
        # print(inspect.currentframe().f_code.co_name)
        n_prime = self.find_predecessor(id)
        if n_prime == id:
            return n_prime
        return self.ask_successor(n_prime)

    def ask_find_successor(self, node_id, id):
        # print(inspect.currentframe().f_code.co_name)
        with self.get_remote_object(node_id) as remote_node:
            succ = remote_node.find_successor(id)
            self.set_id_ip(succ, remote_node.get_id_ip(succ))
            return succ

    def find_predecessor(self, id):
        # print(inspect.currentframe().f_code.co_name)
        n_prime = self.id
        n_prime_succ = self.ask_successor(n_prime)
        while not self.in_between(id, n_prime + 1, n_prime_succ):
            n_prime = self.ask_closest_preceding_finger(n_prime, id)
            n_prime_succ = self.ask_successor(n_prime)
        if id == n_prime_succ:
            return n_prime_succ
        return n_prime

    def closest_preceding_finger(self, id):
        # print(inspect.currentframe().f_code.co_name)
        for i in range(self.bits, 0, -1):
            if self.in_between(self.finger[i].node, self.id + 1, id - 1):
                return self.finger[i].node
        return self.id

    def ask_closest_preceding_finger(self, node_id, id):
        # print(inspect.currentframe().f_code.co_name)
        if node_id == self.id:
            return self.closest_preceding_finger(id)

        with self.get_remote_object(node_id) as remote_node:
            cpf = remote_node.closest_preceding_finger(id)
            self.set_id_ip(cpf, remote_node.get_id_ip(cpf))
            return cpf

    def notify(self, id):
        # print(inspect.currentframe().f_code.co_name)
        if self.in_between(id, self.predecessor + 1, self.id - 1):
            self.predecessor = id

    def ask_notify(self, node_id, id):
        # print(inspect.currentframe().f_code.co_name)
        if node_id == self.id:
            return self.notify(id)

        with self.get_remote_object(node_id) as remote_node:
            remote_node.notify(id)
            remote_node.set_id_ip(id, self.get_id_ip(id))

    def stabilize(self):
        # print(inspect.currentframe().f_code.co_name)
        x = self.ask_predecessor(self.successor)
        if self.in_between(x, self.id + 1, self.successor - 1) and x != self.id:
            self.finger[1].node = x
        self.ask_notify(self.successor, self.id)
        # self.print_finger_table()

    def fix_fingers(self):
        # print(inspect.currentframe().f_code.co_name)
        i = random.randint(1, self.bits)
        self.finger[i].node = self.find_successor(self.finger[i].start)
        # self.print_finger_table()

    def join(self, known_id=None, known_ip=None):
        # print(inspect.currentframe().f_code.co_name)
        if known_id is not None and known_ip is not None:
            self.set_id_ip(known_id, known_ip)
            self.init_fingers(known_id)
            self.update_others()
        else:
            print("First node on the network")
            for i in range(1, self.bits + 1):
                self.finger[i].node = self.id
            self.predecessor = self.id
        print("joined")
        self.joined = True

    def init_fingers(self, node_id):
        # print(inspect.currentframe().f_code.co_name)
        self.finger[1].node = self.ask_find_successor(node_id, self.finger[1].start)
        self.predecessor = self.ask_predecessor(self.successor)
        self.ask_set_predecessor(self.successor, self.id)

        for i in range(1, self.bits):
            if self.in_between(
                self.finger[i + 1].start,
                self.id,
                self.finger[i].node - 1,
            ):
                self.finger[i + 1].node = self.finger[i].node
            else:
                self.finger[i + 1].node = self.ask_find_successor(
                    node_id, self.finger[i + 1].start
                )

    def update_others(self):
        # print(inspect.currentframe().f_code.co_name)
        for i in range(1, self.bits + 1):
            p = self.find_predecessor((self.id - 2 ** (i - 1)) % (2 ** self.bits))

            if p == self.id:
                continue

            self.ask_update_fingers(p, self.id, i)

    def update_fingers(self, s, i):
        # print(inspect.currentframe().f_code.co_name)
        if self.in_between(s, self.id, self.finger[i].node - 1):
            self.finger[i].node = s
            p = self.predecessor

            if p != s:
                self.ask_update_fingers(p, s, i)

    def ask_update_fingers(self, node_id, s, i):
        # print(inspect.currentframe().f_code.co_name)
        if node_id == self.id:
            self.update_fingers(s, i)
            return

        with self.get_remote_object(node_id) as remote_node:
            remote_node.set_id_ip(s, self.get_id_ip(s))
            remote_node.update_fingers(s, i)

    def stabilization(self):
        # print(inspect.currentframe().f_code.co_name)
        while not self.joined:
            time.sleep(7)
        set_interval(self.stabilize, 5).start()
        set_interval(self.fix_fingers, 5).start()

    def start_stabilization(self):
        # print(inspect.currentframe().f_code.co_name)
        threading.Thread(target=self.stabilization).start()

    def print_finger_table(self):
        print("Finger table:")
        print(f"Predecessor: {self.predecessor}")
        fingers = (
            (
                f"{self.finger[i].start} "
                f"{self.finger[i].interval} "
                f"{self.finger[i].node}"
            )
            for i in range(1, self.bits + 1)
        )
        print(str.join(fingers))
        print("------------------------------")

    # check all calls to in_between
    def in_between(self, key, lwb, upb):
        lwb %= 2 ** self.bits
        upb %= 2 ** self.bits

        if lwb <= upb:
            return lwb <= key and key <= upb
        else:
            return (lwb <= key and key <= upb + (2 ** self.bits)) or (
                lwb <= key + (2 ** self.bits) and key <= upb
            )


def set_interval(callback, interval):
    def tread_main():
        while True:
            callback()
            time.sleep(interval)

    return threading.Thread(target=tread_main, daemon=True)


def start_pyro(node):
    pyro_api.serve(
        {node: str(node.id)}, host=node.ip, port=rpc.PYROD_PORT, use_ns=False
    )


if __name__ == "__main__":
    ip = sys.argv[1]
    id = hasha.hash(ip)
    bits = hasha.BIT_NUM

    node = ChordNode(ip, id, bits)
    node.start_stabilization()

    pyro_thread = threading.Thread(target=lambda: start_pyro(node))
    pyro_thread.start()

    if len(sys.argv) > 2:
        known_ip = sys.argv[2]
        known_id = hasha.hash(known_ip)
        node.join(known_id=known_id, known_ip=known_ip)
    else:
        node.join()
