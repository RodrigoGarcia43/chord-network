# Chord

Para ejecutar el proyecto siga las instrucciones siguientes.

```bash
docker build -t jmederosalvarado/chord .
docker network create --subnet 10.0.0.0/24 chord-net
docker-compose up
```

En varias terminales ejecute

```bash
docker exec -it chord-node-{1-8} bash
```

Una vez en el container ejecutar las lineas siguiente.
Nota: La variable `$IP` es seteada automaticamente al ejecutar
el container a traves de `docker-compose`.

```bash
# solo un parametro para el primer nodo de la red
python node.py $IP
```

```bash
# solo un parametro para el primer nodo de la red
python node.py $IP <ip de alguno de los nodos ya en la red>
```

En uno de los container ejecute el cliente de la siguiente
y siga las instrucciones.

```bash
python client.py
```
