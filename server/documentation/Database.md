# D4 core

![](https://www.d4-project.org/assets/images/logo.png)

## D4 core server

D4 core server is a complete server to handle clients (sensors) including the decapsulation of the [D4 protocol](https://github.com/D4-project/architecture/tree/master/format), control of
sensor registrations, management of decoding protocols and dispatching to adequate decoders/analysers.

## Database map

| Key | Value |
| --- | --- |
|  |  |
|  |  |  |

### Server
| Key | Value |
| --- | --- |
| server:hmac_default_key | **hmac_default_key** |

| Set Key | Value |
| --- | --- |
| server:accepted_type          | **accepted type** |
| server:accepted_extended_type | **accepted extended type** |

###### Connection Manager
| Set Key | Value |
| --- | --- |
| active_connection          | **uuid** |
|  |  |
| active_connection:**type**               | **uuid** |
| active_connection_extended_type:**uuid** | **extended type** |
|  |  |
| active_uuid_type2:**uuid** | **session uuid** |
|  |  |
| map:active_connection-uuid-session_uuid:**uuid** | **session uuid** |

| Set Key | Field | Value |
| --- | --- | --- |
| map:session-uuid_active_extended_type | **session_uuid** | **extended_type** |

### Stats
| Zset Key | Field | Value |
| --- | --- | --- |
| stat_uuid_ip:**date**:**uuid**  | **IP** | **number D4 Packets** |
|  |  |  |
| stat_uuid_type:**date**:**uuid** | **type** | **number D4 Packets** |
|  |  |  |
| stat_type_uuid:**date**:**type** | **uuid** | **number D4 Packets** |
|  |  |  |
| stat_ip_uuid:20190519:158.64.14.86 | **uuid** | **number D4 Packets** |
|  |  |  |
|  |  |  |
| daily_uuid:**date** | **uuid** | **number D4 Packets** |
|  |  |  |
| daily_type:**date** | **type** | **number D4 Packets** |
|  |  |  |
| daily_ip:**date** | **IP** | **number D4 Packets** |

### metadata sensors
| Hset Key | Field | Value |
| --- | --- | --- |
| metadata_uuid:**uuid** | first_seen  | **epoch**         |
|                        | last_seen   | **epoch**         |
|                        | description | **description**   |
|                        | Error       | **error message** |

###### Last IP
| List Key | Value |
| --- | --- |
| list_uuid_ip:**uuid** | **IP** |

### metadata types by sensors
| Hset Key | Field | Value |
| --- | --- | --- |
| metadata_uuid:**uuid** | first_seen | **epoch** |
|                        | last_seen  | **epoch** |

| Set Key | Value |
| --- | --- |
| all_types_by_uuid:**uuid** | **type** |
| all_extended_types_by_uuid:**uuid** | **type** |

### analyzers
###### metadata
| Hset Key | Field | Value |
| --- | --- | --- |
| analyzer:**uuid** | last_updated | **epoch** |
|                   | description  | **description** |
|                   | max_size     | **queue max size** |

###### all analyzers by type
| Set Key | Value |
| --- | --- |
| analyzer:**type**              | **uuid** |
| analyzer:254:**extended type** | **uuid** |
