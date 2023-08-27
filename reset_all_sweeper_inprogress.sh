#!/bin/bash

for i in {0..5}; do
  echo "Removing concerto-d-results/$i/sweeper/inprogress"
  rm concerto-d-results/$i/sweeper/inprogress
done
