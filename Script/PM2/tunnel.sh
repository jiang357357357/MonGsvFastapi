#!/usr/bin/env bash
exec ssh -NT \
  -o ServerAliveInterval=30 \
  -o ServerAliveCountMax=3 \
  -o ExitOnForwardFailure=yes \
  -o StrictHostKeyChecking=no \
  -R 0.0.0.0:40302:localhost:40302 \
  -R 0.0.0.0:40031:localhost:40031 \
  ubuntu@1.13.181.58
