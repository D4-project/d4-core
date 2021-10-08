all: d4


hmac: hmac.o sha2.o
	$(CC) sha2.o hmac.o -o hmac

hmac.o: ./others/hmac/hmac_sha2.c ./others/hmac/hmac_sha2.h
	$(CC) -Wall -c ./others/hmac/hmac_sha2.c -o hmac.o

unpack.o: others/uuid/unpack.c others/uuid/uuidP.h
	$(CC) -Wall -c others/uuid/unpack.c -o unpack.o

parse.o: others/uuid/parse.c others/uuid/uuidP.h
	$(CC) -Wall -c others/uuid/parse.c -o parse.o

unparse.o: others/uuid/unparse.c others/uuid/uuidP.h others/uuid/uuid.h
	$(CC) -Wall -c others/uuid/unparse.c -o unparse.o

pack.o: others/uuid/pack.c others/uuid/uuidP.h
	$(CC) -Wall -c others/uuid/pack.c -o pack.o

gen_uuid.o: others/uuid/gen_uuid.c  others/uuid/uuidP.h others/uuid/randutils.h
	$(CC) -Wall -c others/uuid/gen_uuid.c  -o gen_uuid.o

randutils.o: others/uuid/randutils.c others/uuid/randutils.h
	$(CC) -Wall -c others/uuid/randutils.c -o randutils.o

sha2.o: ./others/hmac/sha2.c ./others/hmac/sha2.h
	$(CC) -c ./others/hmac/sha2.c -o sha2.o

clean:
	- rm -rf *.o hmac

d4:	d4.o sha2.o hmac.o unpack.o unparse.o pack.o gen_uuid.o randutils.o parse.o
	$(CC) -Wall -o d4 d4.o hmac.o sha2.o unpack.o pack.o unparse.o gen_uuid.o randutils.o parse.o

d4.o:	d4.c
	$(CC) -Wall -c d4.c
