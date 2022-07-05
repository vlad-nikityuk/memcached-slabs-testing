# memcached-slabs-testing

1. Run Grafana, Influx and Memcached

```sh
$ docker compose up
```

2. Run stats collector and testing script

```sh
$ pip install -r requirements.txt
...
$ python test.py
...
$ python stats.py
```

3. Import dashboard `grafana_dashboard.json` to Grafana (http://localhost:3000)
