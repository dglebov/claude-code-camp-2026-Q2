# CircleMUD Apple Container Compose

This setup builds CircleMUD 3.1 from the official source archive and runs it on port 4000.

I'm running my lab on a MacBook, which includes a native Apple container application. I decided to try something new: using OCI images with this Apple container tool. 
Below are the steps for setting up the infrastructure and running the images using the native Apple container application. 

## Build Image and Run 

```sh
container build -t infrastructure

container run -d --name infra -p 4000:4000 infrastructure:latest
```

### Confirm container is runnig 

```sh
container ls
ID        IMAGE                                                OS     ARCH   STATE    IP               CPUS  MEMORY   STARTED
infra     infrastructure:latest                                linux  arm64  running  192.168.64.4/24  4     1024 MB  2026-07-17T11:49:13Z
```

Connect with a MUD client, telnet, or netcat:

```sh
telnet localhost 4000
```

The `circlemud-lib` Docker volume stores persistent game data, including player files and world state.
