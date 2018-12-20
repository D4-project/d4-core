#ifndef D4_H
#define D4_H

#include "others/hmac/hmac_sha2.h"

#define ND4PARAMS 7
#define NERRORS 100
#define SZCONFVALUE 1024
#define SZERRVALUE 1024
#define SZHMAC 32

#define STDIN "stdin"
#define STDOUT "stdout"
#define MAXSNAPLEN 65535
#define SZUUID 16
#define SZUUID_TEXT 37
#define SZD4HDR 62
#define INSERT_ERROR(...) do { \
    if (d4->err_idx < NERRORS) \
        snprintf(d4->errors[d4->err_idx],SZERRVALUE,__VA_ARGS__); \
        d4->err_idx++;\
    } while(0)

typedef struct d4_header_s {
    uint8_t  version;
    uint8_t type;
    uint8_t uuid[SZUUID];
    uint64_t timestamp;
    uint8_t hmac[SZHMAC];
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
    char conf[ND4PARAMS][SZCONFVALUE];
    char errors[NERRORS][SZERRVALUE];
    int err_idx;
    d4_header_t header;
    hmac_sha256_ctx *ctx;
} d4_t;


/* D4 configuration is a directory structure shown below (like proc filesytem)
 * d4-conf/snaplen
 * d4-conf/caplen
 * d4-conf/uuid
 * d4-conf/collector
 */

const char* d4params[] = {"uuid", "snaplen", "key", "version", "source", "destination","type"};

#define UUID 0
#define SNAPLEN 1
#define KEY 2
#define VERSION 3
#define SOURCE 4
#define DESTINATION 5
#define TYPE 6

#endif
