#!/bin/bash

render() {
  sedStr="
  s!%%PY_VERSION%%!$version!g;
"

  sed -r "$sedStr" $1
}

versions=(3.5 3.6 3.7 3.8 3.9)
for version in ${versions[*]}; do
  [ -d $version ] || mkdir $version
  render Dockerfile.template >$version/Dockerfile
  docker build -t resttest3:py-$version -f $version/Dockerfile .
done
