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

/*
 * Generate a uuid if no one was set
 */
void  d4_update_uuid(d4_t* d4)
{
    uuid_t uuid;
    int fd,ret;
    char* filename;
    char* uuid_text;

    if (d4->conf[UUID][0] == 0){
        uuid_generate(uuid);
        memcpy(d4->conf[UUID], uuid, SZUUID);
        filename = calloc(1,2*FILENAME_MAX);
        uuid_text = calloc(1, SZUUID_TEXT);
        if ((filename != NULL) && (uuid != NULL)) {
            snprintf(filename, 2*FILENAME_MAX, "%s/%s",d4->confdir, d4params[UUID]);
            fd = open(filename, O_CREAT  |  O_WRONLY, S_IRUSR  |S_IWUSR);
            if (fd > 0) {
                uuid_unparse(uuid, uuid_text);
                ret =  write(fd, uuid_text, SZUUID_TEXT-1);
                if (ret < 0) {
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
    if (strlen(d4->conf[SOURCE]) > strlen(STDIN)) {
        if (!strncmp(d4->conf[SOURCE],STDIN, strlen(STDIN))) {
            d4->source.fd = STDIN_FILENO;
        }
    }

    //TODO implement other destinations file, fifo unix_socket ...
    if (strlen(d4->conf[DESTINATION]) > strlen(STDOUT)) {
        if (!strncmp(d4->conf[DESTINATION],STDOUT, strlen(STDOUT))) {
            d4->destination.fd = STDOUT_FILENO;
        }
    }
    d4->snaplen  = atoi(d4->conf[SNAPLEN]);

    d4_update_uuid(d4);

    if ((d4->snaplen < 0)  || (d4->snaplen > MAXSNAPLEN)) {
        d4->snaplen = 0;
    }

    printf("TEST snaplen %d stdin %d stdout %d\n", d4->snaplen, STDIN_FILENO, STDOUT_FILENO);
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
            } else {
                d4->errno_copy = errno;
                INSERT_ERROR("Failed to load %s", d4params[i]);
            }
        }
    }
    return d4_check_config(d4);
}

void usage(void)
{
    printf("d4 client help\n");
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
    bzero(&d4->header,sizeof(d4->header));
    d4->header.version = atoi(d4->conf[VERSION]);
    //FIXME length handling
    strncpy((char*)&(d4->header.uuid), d4->conf[UUID], SZUUID);
    d4->header.type = atoi(d4->conf[TYPE]);
}

void d4_update_header(d4_t* d4, ssize_t nread) {
    struct timeval tv;
    bzero(&tv,sizeof(struct timeval));
    gettimeofday(&tv,NULL);
    d4->header.timestamp = tv.tv_sec;
    //TODO hmac
    d4->header.size=nread;
}

//Core routine. Transfers data from the source to the destinations
void d4_transfert(d4_t* d4)
{
    ssize_t nread;
    char* buf;

    buf = calloc(1, d4->snaplen);
    //TODO error handling -> insert error message
    if (!buf)
        return;

    d4_prepare_header(d4);
    while ( 1 ) {
        //In case of errors see block of 0 bytes
        bzero(buf, d4->snaplen);
        nread = read(d4->source.fd, buf, d4->snaplen);
        if ( nread > 0 ) {
            d4_update_header(d4, nread);
            write(d4->destination.fd, &d4->header, sizeof(d4->header));
            write(d4->destination.fd,buf,nread);
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
