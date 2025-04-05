#!/bin/bash

if [[ -z "$NEJUDGE_NOUPDATE" ]]; then
  git pull origin master --rebase
fi
