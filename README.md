# D4 core

![](https://www.d4-project.org/assets/images/logo.png)

D4 core are software components used in the D4 project. The software includes everything to create your own sensor network or connect
to an existing sensor network using simple clients.

## D4 core client

[D4 core client](https://github.com/D4-project/d4-core/tree/master/client) is a simple and minimal implementation of the [D4 encapsulation protocol](https://github.com/D4-project/architecture/tree/master/format). There is also a [portable D4 client](https://github.com/D4-project/d4-goclient) in Go including the support for the SSL/TLS connectivity.

### Requirements

- Unix-like operating system
- make
- a recent C compiler

### Usage

The D4 client can be used to stream any byte stream towards a D4 server.

As an example, you directly stream tcpdump output to a D4 server with the following
script:

````
tcpdump -n -s0 -w - | ./d4 -c ./conf | socat - OPENSSL-CONNECT:$D4-SERVER-IP-ADDRESS:$PORT,verify=0
````

~~~~
d4 - d4 client
Read data from the configured <source> and send it to <destination>

Usage: d4 -c  config_directory

Configuration

The configuration settings are stored in files in the configuration directory
specified with the -c command line switch.

Files in the configuration directory

key         - is the private HMAC-SHA-256-128 key.
              The HMAC is computed on the header with a HMAC value set to 0
              which is updated later.
snaplen     - the length of bytes that is read from the <source>
version     - the version of the d4 client
type        - the type of data that is send. pcap, netflow, ...
source      - the source where the data is read from
destination - the destination where the data is written to
~~~~

### Installation

~~~~
cd client
git submodule init
git submodule update
~~~~

## D4 core server

D4 core server is a complete server to handle clients (sensors) including the decapsulation of the [D4 protocol](https://github.com/D4-project/architecture/tree/master/format), control of
sensor registrations, management of decoding protocols and dispatching to adequate decoders/analysers.

### Requirements

- Python 3.6
- GNU/Linux distribution

### Installation

~~~~
cd server
./install_server.sh
./LAUNCH.sh -l
~~~~

The web interface is accessible via `http://127.0.0.1:7000/`

### Screenshots of D4 core server management

![](https://raw.githubusercontent.com/D4-project/d4-core/master/doc/images/main.png)
![](https://raw.githubusercontent.com/D4-project/d4-core/master/doc/images/sensor-mgmt.png)
![](https://raw.githubusercontent.com/D4-project/d4-core/master/doc/images/server-mgmt.png)
