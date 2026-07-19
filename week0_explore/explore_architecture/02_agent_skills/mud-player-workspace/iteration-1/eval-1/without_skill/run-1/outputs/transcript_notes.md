# Transcript notes — attempt to log into MUD character

No prior context was available about which MUD, host, or credentials to use. Ran the following exploratory commands:

1. Probed common MUD/telnet ports on localhost with `nc`:
   ```
   for port in 4000 4001 23 6000 8888 5000; do
     echo "--- Trying localhost:$port ---"
     (echo -e "look\nquit" | nc -w 2 localhost $port 2>&1) || echo "no connection on $port"
   done
   ```
   Result: only `localhost:4000` responded (with telnet client-detection negotiation bytes). Ports 4001, 23, 6000, 8888, 5000 gave no connection.

2. Re-connected to `localhost:4000` with a longer read window (`nc -w 5`, `cat -v`) to see the raw banner text — confirmed it was doing telnet protocol negotiation ("Attempting to Detect Client...", "Collecting Protocol Information...").

3. Used a short Python script (`socket.create_connection`) to capture the full raw banner bytes without a client-side timeout truncating it early:
   ```python
   import socket
   s = socket.create_connection(("localhost", 4000), timeout=5)
   s.settimeout(2)
   data = b""
   try:
       while True:
           chunk = s.recv(4096)
           if not chunk:
               break
           data += chunk
   except socket.timeout:
       pass
   print(repr(data))
   s.close()
   ```
   Result: server identified itself as "TBAMUD 2025" (CircleMUD/DikuMUD-derived codebase) and presented the prompt:
   `By what name do you wish to be known?`

Stopped at this point — no character name or password was known, so no login attempt (successful or guessed) was made. No `look` command was ever sent to an authenticated session. Did not explore any local repo directories for credentials/config, per task scope (this was a network-probe-only investigation based on the user's prompt).
