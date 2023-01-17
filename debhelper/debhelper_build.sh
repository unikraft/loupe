#!/bin/bash

target=$1

mkdir -p $target-test
cd $target-test

apt-get build-dep -y $target
# Get the sources
apt-get source $target

# Go the the resulting directory
cd $target-*

# Build the package

DEB_BUILD_OPTIONS=nocheck dpkg-buildpackage -us -uc --build=full
