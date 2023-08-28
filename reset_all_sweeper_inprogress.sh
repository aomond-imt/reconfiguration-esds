#!/bin/bash

for i in {0..99}; do
  echo "Removing concerto-d-results/$i/sweeper/inprogress"
  rm concerto-d-results/$i/sweeper/inprogress
done
