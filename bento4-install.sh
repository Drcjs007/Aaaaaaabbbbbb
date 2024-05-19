#!/bin/bash
wget -qO- https://github.com/axiomatic-systems/Bento4/archive/refs/heads/master.zip -O bento4-master.zip
unzip bento4-master.zip
cd Bento4-master
mkdir cmakebuild
cd cmakebuild
cmake -DCMAKE_BUILD_TYPE=Release ..
make
make install
