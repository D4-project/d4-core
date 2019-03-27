# D4 core

![](https://www.d4-project.org/assets/images/logo.png)

## D4 core server

D4 core server is a complete server to handle clients (sensors) including the decapsulation of the [D4 protocol](https://github.com/D4-project/architecture/tree/master/format), control of
sensor registrations, management of decoding protocols and dispatching to adequate decoders/analysers.

### Requirements

- Python 3.6
- GNU/Linux distribution

### Installation

###### Install D4 server
~~~~
cd server
./install_server.sh
~~~~
Create or add a pem in [d4-core/server](https://github.com/D4-project/d4-core/tree/master/server) :
~~~~
cd gen_cert
./gen_root.sh
./gen_cert.sh
cd ..
~~~~


###### Launch D4 server
~~~~
./LAUNCH.sh -l
~~~~

The web interface is accessible via `http://127.0.0.1:7000/`

### Updating web assets
To update javascript libs run:
~~~~
cd web
./update_web.sh
~~~~

### Notes

- All server logs are located in ``d4-core/server/logs/``
- Close D4 Server: ``./LAUNCH.sh -k``

### Screenshots of D4 core server management

![](https://raw.githubusercontent.com/D4-project/d4-core/master/doc/images/main.png)
![](https://raw.githubusercontent.com/D4-project/d4-core/master/doc/images/sensor-mgmt.png)
![](https://raw.githubusercontent.com/D4-project/d4-core/master/doc/images/server-mgmt.png)
![](https://raw.githubusercontent.com/D4-project/d4-core/master/doc/images/analyzer-mgmt.png)
![](https://raw.githubusercontent.com/D4-project/d4-core/master/doc/images/server-mgmt2.png)
