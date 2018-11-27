#ifndef D4_H
#define D4_H

typedef struct d4_header_s {
    uint8_t  version;
    uint8_t type;
    uint8_t uuid[128];
    uint64_t timestamp;
    uint8_t hmac[256];
    uint32_t size;
} d4_header_t;

// Information about the source
typedef struct source_s {
    int fd;
} source_t;

//Information about the destination
//Write data to stdout, fifo, shared memory segment
typedef struct destination_s {
    int fd;
} destination_t;

typedef struct d4_s {
    source_t source;
    destination_t destination;
    char confdir[FILENAME_MAX];
    int snaplen;
    int caplen;
    int d4_error;
    int errno_copy;
} d4_t;



/* D4 configuration is a directory structure shown below (like proc filesytem)
 * d4-conf/snaplen
 * d4-conf/caplen
 * d4-conf/uuid
 * d4-conf/collector
 */

const char* d4params[] = {"uuid", "snaplen", "caplen", "timestamp", "collector"};
#define ND4PARAMS 5

#define UUID 0
#define SNAPLEN 1
#define CAPLEN 2
#define TIMESTAMP 3
#define COLLECTOR 4

#endif
