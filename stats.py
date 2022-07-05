from datetime import datetime
from pymemcache.client.base import Client
from influxdb import InfluxDBClient
from time import time, sleep


STATS_TO_SKIP = set(b'version', b'libevent')


influxdb = InfluxDBClient(host='localhost', port=8086, database="db0")
client = Client('localhost')


def to_str_dict(d):
    return {k.decode('utf-8'):v for k, v in d.items()}


def create_point(measurement, value, dt, tags={}):
    return {
        "measurement": measurement,
        "tags": tags,
        "time": dt,
        "fields": {"value": value}
    }


while True:
    sleep(1)
    dt = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    points = [
        create_point("mem__" + k, v, dt)
        for k, v in to_str_dict(client.stats()).items()
        if k not in STATS_TO_SKIP
    ] + [
        create_point("slabs__" + k.split(":")[1], v, dt, tags={"slab": k.split(":")[0]})
        for k, v in to_str_dict(client.stats("slabs")).items()
        if k[0].isdigit()
    ]

    influxdb.write_points(points)
    print(f"Done ... {time()}")
