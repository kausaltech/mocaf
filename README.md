# Mobility Carbon Footprint API

## GraphQL API

The main interaction with Mocaf is done over a GrahpQL API. The main API
endpoint (and interactive GraphiQL browser) is located at `/v1/graphql/`.

### Authentication

Most GraphQL queries are allowed to access data for only one device.
A device is identified by a UUID. Authentication is provided
using a randomly generated access token.

The UUID and the access token are passed using a global `@device` directive
for the query (or mutation):

```graphql
query @device(uuid: "0bb26707-1016-4f60-92e3-62c209040cc2", token: "23730161-54a5-4c06-b0e9-c0533bcc911e") {
  trips {
    id
    legs {
      mode {
        identifier
        name
      }
      length
      carbonFootprint
      startTime
      startLoc
      endTime
      endLoc
    }
  }
}
```

### Mutations

#### Enable Mocaf

The first interaction with the API should usually be the `enableMocaf` mutation.
It will create the access token and pass it as a response to the mutation.

> :warning: **Remember to save the access token!** If you lose the access token, you are locked out of the UUID, as all future queries for that UUID will require passing the token.

This mutation is not authenticated, and will fail if a token has already been generated
for a device.

Mutation:

```graphql
mutation {
  enableMocaf(uuid:"4922d7d7-956f-40d0-803f-7d06a0c75d40") {
    ok
    token
  }
}
```

Response:

```json
{
  "data": {
    "enableMocaf": {
      "ok": true,
      "token": "189c482f-7607-4d12-a0e4-329d9e7e06a9"
    }
  }
}
```

#### Disable Mocaf

Calling the `disableMocaf` mutation will disable the carbon footprint calculator
and prevent any other device-specific requests from working except the `enableMocaf`
mutation.

#### Update leg

The `updateLeg` mutation allows the user to change leg-specific information such
as the transport mode or the number of passengers in the car.

```graphql
mutation @device(uuid: "0bb26707-1016-4f60-92e3-62c209040cc2", token: "23730161-54a5-4c06-b0e9-c0533bcc911e") {
  updateLeg(leg: "2", mode: "car", nrPassengers: 2) {
    ok
  }
}
```

## Installation

### Development

Install the required Python packages:

```shell
pip install -r requirements.txt
```

Create a file called `local_settings.py` in your repo root with the following contents:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'mocaf',
        'ATOMIC_REQUESTS': True,
    }
}
```

Create a Postgres database and the postgis extension:

```shell
createdb mocaf
sudo -u postgres psql -c "CREATE EXTENSION postgis" mocaf
```

If you intend to run the tests, you need to make sure the extension is also created whenever the test database is
created, which happens every time you run `pytest`. If you always run the tests with the `--reuse-db` flag, you can
create the extension once for the database that is being re-used and you'll be fine:

```shell
createdb test_mocaf
sudo -u postgres psql -c "CREATE EXTENSION postgis" test_mocaf
```

If you don't use the `--reuse-db` flag, the extension needs to be created along with the database every time you run
`pytest`, so you can run the following. Bear in mind, however, that this enables the postgis extension for *any* new
database.

```shell
sudo -u postgres psql -d template1 -c "CREATE EXTENSION IF NOT EXISTS postgis"
```

Run migrations:

```shell
python manage.py migrate
```

Create a superuser:
> You might need the following translations during the createsuperuser operation: käyttäjätunnus = username, sähköpostiosoite = e-mail

```shell
python manage.py createsuperuser
```


### TODO

- Fix viterbi
  - Remove heuristic smoothing
- Incorporate gis for vehicle detection
- Check GTFS vs client GPS sync
- noProfit