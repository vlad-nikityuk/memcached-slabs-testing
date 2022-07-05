import sys
import random
import string

from time import sleep, time

from cachetools import TTLCache

from humanfriendly import format_timespan
from pymemcache.client.base import Client

NS = string.ascii_letters + string.digits

from influxdb import InfluxDBClient
influxdb = InfluxDBClient(host='localhost', port=8086, database="db0")
from datetime import datetime

def create_point(measurement, value, dt, tags={}):
    return {
        "measurement": measurement,
        "tags": tags,
        "time": dt,
        "fields": {"value": value}
    }


client = Client('localhost')
global_start = time()
rand = random.Random()

DEBUG=False

if "--debug" in sys.argv:
    DEBUG = True

KEY_LEN = 20
HIT_RATE_MEM_LEN=1_000_000_000
TTL=20*60 if not DEBUG else 60
STAT_WINDOW=10 if not DEBUG else 1


def get_random_key(l=KEY_LEN):
    return ''.join(random.choice(NS) for i in range(l))


def get_size(item_size, delta):
    if rand.randint(0, 100) <= 80:
        return item_size + rand.randint(0, delta)
    elif rand.randint(0, 100) <= 95:
        return rand.randint(10, 2000)
    else:
        return rand.randint(2000, 10_000)
    

def run_test(item_size, delta, target_hit_rate, run_for):
    test_start = time()    
    
    hit_rate_mem = TTLCache(maxsize=HIT_RATE_MEM_LEN, ttl=TTL)

    stats_hits = 0
    stats_misses = 0
    start_time = time()
    target_hit_rate_100 = target_hit_rate * 100

    while True:        
        sleep(0 if not DEBUG else 0.1)
        coin = rand.randint(0, 100)
        if coin <= target_hit_rate_100:
            # Hit
            all_available_keys = list(hit_rate_mem.keys())
            
            if not all_available_keys:
                stats_misses += 1
            else:
                random_key = all_available_keys[rand.randint(0, len(all_available_keys) - 1)]
                
                val = client.get(random_key)
                if val is not None:
                    stats_hits += 1
                else:
                    stats_misses += 1 
        else:
            # Miss
            k = get_random_key()

            val = client.get(k)

            stats_misses += 1
            
            data_n = get_size(item_size, delta)
            data = rand.getrandbits(data_n * 8).to_bytes(data_n, 'little')
            client.set(k, data, expire=TTL)
            hit_rate_mem[k] = 1
        
        if time() - start_time >= STAT_WINDOW:
            total = stats_hits + stats_misses
            elapsed_str = format_timespan(time() - test_start)
            print(f"Hit rate: {stats_hits/total :.2f} (hits: {stats_hits}, misses: {stats_misses}) elapsed: {elapsed_str}")

            dt = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            points = [
                create_point("test__hit_rate", stats_hits/total, dt),
                create_point("test__hits", stats_hits, dt),
                create_point("test__misses", stats_misses, dt),
                create_point("test__total", total, dt),
                create_point("test__hit_rate_mem_keys", len(hit_rate_mem.keys()), dt),
            ]
            influxdb.write_points(points)

            stats_hits = 0
            stats_misses = 0
            start_time = time()

            hit_rate_mem.expire()
        
        if time() - test_start >= run_for:
            return


run_test(300, 50, target_hit_rate=0.7, run_for=30*60)

print("--------------------------------------------------------------------------------------------------------------------------------")

run_test(700, 50, target_hit_rate=0.7, run_for=30*60)
