import hasha
import rpc


def get_value_pos(known_id, known_ip, key):
    with rpc.get_remote_object(known_id, known_ip) as remote_node:
        return remote_node.find_successor(key)


if __name__ == "__main__":
    known_ip = input("Enter known ip: ")
    key = input("Enter key to search for: ")
    key = int(key)

    known_id = hasha.hash(known_ip)

    node = get_value_pos(known_id, known_ip, key)

    print(f"The key {key} is handled by node {node}")
