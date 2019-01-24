# D4 core

D4 core are software components used in the D4 project. The software includes everything to create your own sensor network or connect
to an existing sensor network using simple clients.

## D4 core client

[D4 core client](https://github.com/D4-project/d4-core/tree/master/client) is a simple and minimal implementation of the [D4 encapsulation protocol](https://github.com/D4-project/architecture/tree/master/format).

### Requirements

- Unix-like operating system
- make
- a recent C compiler

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

