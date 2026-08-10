#!/usr/bin/env bash
exec ssh -NT \
  -o ServerAliveInterval=30 \
  -o ServerAliveCountMax=3 \
  -o ExitOnForwardFailure=yes \
  -o StrictHostKeyChecking=no \
  -R 127.0.0.1:40302:localhost:40302 \
  -R 127.0.0.1:40031:localhost:40031 \
  ubuntu@1.13.181.58
