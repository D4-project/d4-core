all: d4


hmac: hmac.o sha2.o
	$(CC) sha2.o hmac.o -o hmac

hmac.o: ./others/hmac/hmac_sha2.c ./others/hmac/hmac_sha2.h
	$(CC) -Wall -c ./others/hmac/hmac_sha2.c -o hmac.o

sha2.o: ./others/hmac/sha2.c ./others/hmac/sha2.h
	$(CC) -c ./others/hmac/sha2.c -o sha2.o

clean:
	- rm -rf *.o hmac

d4:	d4.o sha2.o hmac.o
	gcc -Wall -o d4 d4.o hmac.o sha2.o -luuid

d4.o:	d4.c
	gcc -Wall -c d4.c
