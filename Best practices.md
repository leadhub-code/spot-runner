Best Practices
==============

Catch shell script errors
-------------------------

I recommend to put this at the start of the shell script:

```shell
set -e
```

See https://www.gnu.org/software/bash/manual/html_node/The-Set-Builtin.html


Redirect stderr to stdout
-------------------------

If you are executing a shell script over SSH – probably some bootstrap script to setup the instance – it may happen that outputs in stdout and stderr will not look synchronized.

I recommend to put this at the start of the shell script:

```bash
exec 2>&1
```




