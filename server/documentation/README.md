#  API DOCUMENTATION

## General

### Automation key

The authentication of the automation is performed via a secure key available in the D4 UI interface. Make sure you keep that key secret. It gives access to the entire database! The API key is available in the ``Settings`` menu under ``My Profile``.

The authorization is performed by using the following header:

~~~~
Authorization: YOUR_API_KEY
~~~~
### Accept and Content-Type headers

When submitting data in a POST, PUT or DELETE operation you need to specify in what content-type you encoded the payload. This is done by setting the below Content-Type headers:

~~~~
Content-Type: application/json
~~~~

Example:

~~~~
curl --header "Authorization: YOUR_API_KEY" --header "Content-Type: application/json" https://D4_URL/
~~~~

## Sensor Registration

### Register a sensor: `api/v1/add/sensor/register`<a name="add_sensor_register"></a>

#### Description
Register a sensor.

**Method** : `POST`

#### Parameters
- `uuid`
  - sensor uuid
  - *uuid4*
  - mandatory

- `hmac_key`
  - sensor secret key
  - *binary*
  - mandatory

- `description`
  - sensor description
  - *str*

- `mail`
  - user mail
  - *str*

#### JSON response
- `uuid`
  - sensor uuid
  - *uuid4*

#### Example
```
curl https://127.0.0.1:7000/api/v1/add/sensor/register --header "Authorization: iHc1_ChZxj1aXmiFiF1mkxxQkzawwriEaZpPqyTQj " -H "Content-Type: application/json" --data @input.json -X POST
```

#### input.json Example
```json
  {
    "uuid": "ff7ba400-e76c-4053-982d-feec42bdef38",
    "hmac_key": "...HMAC_KEY..."
  }
```

#### Expected Success Response
**HTTP Status Code** : `200`

```json
  {
    "uuid": "ff7ba400-e76c-4053-982d-feec42bdef38",
  }
```

#### Expected Fail Response

**HTTP Status Code** : `400`
```json
  {"status": "error", "reason": "Mandatory parameter(s) not provided"}
  {"status": "error", "reason": "Invalid uuid"}
```

**HTTP Status Code** : `409`
```json
  {"status": "error", "reason": "Sensor already registred"}
```
