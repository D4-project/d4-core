#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <getopt.h>
#include <string.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>
#include <sys/time.h>

#include <uuid/uuid.h>
#include "d4.h"
//


void usage(void)
{
    printf("d4 - d4 client\n");
    printf("Read data from the configured <source> and send it to <destination>\n");
    printf("\n");
    printf("Usage: d4 -c  config_directory\n");
    printf("\n");

    printf("Configuration\n\n");
    printf("The configuration settings are stored in files in the configuration directory\n");
    printf("specified with the -c command line switch.\n\n");
    printf("Files in the configuration directory\n");
    printf("\n");
    printf("key         - is the private HMAC-SHA-256-128 key.\n");
    printf("              The HMAC is computed on the header with a HMAC value set to 0\n");
    printf("              which is updated later.\n");
    printf("snaplen     - the length of bytes that is read from the <source>\n");
    printf("version     - the version of the d4 client\n");
    printf("type        - the type of data that is send. pcap, netflow, ...\n");
    printf("source      - the source where the data is read from\n");
    printf("destination - the destination where the data is written to\n");
}

/*
 * Generate a uuid if no one was set.
 * If no errors occured textual representation of uuid is stored in the
 * configuration array
 */
void  d4_update_uuid(d4_t* d4)
{
    uuid_t uuid;
    int fd,ret;
    char* filename;
    char* uuid_text;

    if (d4->conf[UUID][0] == 0){
        uuid_generate(uuid);
        filename = calloc(1,2*FILENAME_MAX);
        uuid_text = calloc(1, SZUUID_TEXT);
        if ((filename != NULL) && (uuid != NULL)) {
            snprintf(filename, 2*FILENAME_MAX, "%s/%s",d4->confdir, d4params[UUID]);
            fd = open(filename, O_CREAT  |  O_WRONLY, S_IRUSR  |S_IWUSR);
            if (fd > 0) {
                uuid_unparse(uuid, uuid_text);
                ret =  write(fd, uuid_text, SZUUID_TEXT-1);
                if (ret > 0) {
                    memcpy(d4->conf[UUID], uuid_text, SZUUID_TEXT);
                } else {
                    d4->errno_copy = errno;
                }
                close(fd);
            } else {
                // Cannot open file
                d4->errno_copy = errno;
            }
        }
        /* If there is an error the uuid is not stored and a new one is
         * generated for the next boot
         */
     }
}

int d4_check_config(d4_t* d4)
{
    // TODO implement other sources, file, fifo, unix_socket ...
    if (strlen(d4->conf[SOURCE]) >= strlen(STDIN)) {
        if (!strncmp(d4->conf[SOURCE],STDIN, strlen(STDIN))) {
            d4->source.fd = STDIN_FILENO;
        }
    }

    //TODO implement other destinations file, fifo unix_socket ...
    if (strlen(d4->conf[DESTINATION]) >= strlen(STDOUT)) {
        if (!strncmp(d4->conf[DESTINATION],STDOUT, strlen(STDOUT))) {
            d4->destination.fd = STDOUT_FILENO;
        }
    }
    d4->snaplen  = atoi(d4->conf[SNAPLEN]);

    d4_update_uuid(d4);

    if ((d4->snaplen < 0)  || (d4->snaplen > MAXSNAPLEN)) {
        d4->snaplen = 0;
    }

    //FIXME Check other parameters
    if ((atoi(d4->conf[VERSION])>0) &&   ( d4->destination.fd > 0 ) && ( d4->snaplen >0 )) {
        return 1;
    }
    return -1;
}

//Returns -1 on error, 0 otherwise
int d4_load_config(d4_t* d4)
{
    int i;
    int fd;
    char *buf;
    buf=calloc(1,2*FILENAME_MAX);
    if (buf) {
        for (i=0; i < ND4PARAMS; i++) {
            snprintf(buf,2*FILENAME_MAX, "%s/%s",d4->confdir, d4params[i]);
            fd = open(buf,O_RDONLY);
            if (fd > 0) {
                //FIXME error handling
                read(fd, d4->conf[i], SZCONFVALUE);
                close(fd);
            } else {
                d4->errno_copy = errno;
                INSERT_ERROR("Failed to load %s", d4params[i]);
            }
        }
    }
    return d4_check_config(d4);
}

d4_t* d4_init(char* confdir)
{
    d4_t* out;
    int i;
    out = calloc(1,sizeof(d4_t));
    if (out) {
        strncpy(out->confdir, confdir, FILENAME_MAX);
    }

    for  (i=0; i< ND4PARAMS; i++) {
        bzero(out->conf[i],SZCONFVALUE);
    }
    // Do other inititalization stuff here
    return out;
}



void d4_prepare_header(d4_t* d4)
{
    char uuid_text[24];
    uuid_t uuid;

    bzero(&d4->header,sizeof(d4->header));
    bzero(&uuid_text, 24);
    d4->header.version = atoi(d4->conf[VERSION]);
    if (!uuid_parse(d4->conf[UUID],uuid)) {
        memcpy(d4->header.uuid, uuid, SZUUID);
    }
    // If UUID cannot be parsed it is set to 0
    d4->header.type = atoi(d4->conf[TYPE]);

    d4->ctx = calloc(sizeof(hmac_sha256_ctx),1);
    if (d4->ctx) {
        //FIXME check cast of the key
        hmac_sha256_init(d4->ctx, (uint8_t*)d4->conf[KEY], strlen(d4->conf[KEY]));
    }
}

void d4_update_header(d4_t* d4, ssize_t nread) {
    struct timeval tv;
    bzero(&tv,sizeof(struct timeval));
    gettimeofday(&tv,NULL);
    d4->header.timestamp = tv.tv_sec;
    d4->header.size=nread;
}

//Core routine. Transfers data from the source to the destinations
void d4_transfert(d4_t* d4)
{
    ssize_t nread;
    ssize_t n;
    char* buf;
    unsigned char* hmac;
    unsigned char* hmaczero;

    buf = calloc(1, d4->snaplen);
    hmac = calloc(1,SZHMAC);
    hmaczero = calloc(1,SZHMAC);
    //TODO error handling -> insert error message
    if ((buf == NULL) && (hmac == NULL) && (hmaczero == NULL))
        return;

    d4_prepare_header(d4);
    while ( 1 ) {
        //In case of errors see block of 0 bytes
        bzero(buf, d4->snaplen);
        nread = read(d4->source.fd, buf, d4->snaplen);
        if ( nread > 0 ) {
            d4_update_header(d4, nread);
            //Do HMAC on header and payload. HMAC field is 0 during computation
            if (d4->ctx) {
                hmac_sha256_reinit(d4->ctx);
		hmac_sha256_update(d4->ctx, (const unsigned char*)&d4->header.version, sizeof(uint8_t));
		hmac_sha256_update(d4->ctx, (const unsigned char*)&d4->header.type, sizeof(uint8_t));
		hmac_sha256_update(d4->ctx, (const unsigned char*)&d4->header.uuid, SZUUID);
		hmac_sha256_update(d4->ctx, (const unsigned char*)&d4->header.timestamp, sizeof(uint64_t));
		hmac_sha256_update(d4->ctx, (const unsigned char*) hmaczero, SZHMAC);
		hmac_sha256_update(d4->ctx, (const unsigned char*)&d4->header.size, sizeof(uint32_t));
		hmac_sha256_update(d4->ctx, (const unsigned char*)buf, nread);
		hmac_sha256_final(d4->ctx, hmac, SZHMAC);
                //Add it to the header
                memcpy(d4->header.hmac, hmac, SZHMAC);
            }
            n = 0;
            n+=write(d4->destination.fd, &d4->header.version, sizeof(uint8_t));
            n+=write(d4->destination.fd, &d4->header.type, sizeof(uint8_t));
            n+=write(d4->destination.fd, &d4->header.uuid, SZUUID);
            n+=write(d4->destination.fd, &d4->header.timestamp, sizeof(uint64_t));
            n+=write(d4->destination.fd, &d4->header.hmac, SZHMAC);
            n+=write(d4->destination.fd, &d4->header.size, sizeof(uint32_t));
            n+=write(d4->destination.fd,buf,nread);
            if (n != SZD4HDR + nread) {
                fprintf(stderr,"Incomplete header written. abort to let consumer known that the packet is corrupted\n");
                abort();
            }
        } else{
            //FIXME no data available, sleep, abort, retry
            break;
        }
    }
}

int main (int argc, char* argv[])
{
    int opt;
    char* confdir;
    d4_t* d4;

    confdir=calloc(1,FILENAME_MAX);
    if (!confdir)
        return EXIT_FAILURE;

    while ((opt = getopt(argc, argv, "c:h")) != -1) {
        switch (opt) {
            case 'h':
                usage();
                return EXIT_SUCCESS;
            case 'c':
                strncpy(confdir, optarg, FILENAME_MAX);
                break;
            default:
                fprintf(stderr,"An invalid command line argument was specified\n");
        }
    }
    if (!confdir[0]){
        fprintf(stderr,"A config directory must be specified\n");
        return EXIT_FAILURE;
    }


    d4 = d4_init(confdir);
    free(confdir);
    if (d4_load_config(d4)) {
        d4_transfert(d4);
    }

    return EXIT_SUCCESS;
}
