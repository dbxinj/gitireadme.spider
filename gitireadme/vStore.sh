# store every version of an article

basePath=dist
#if [! -d "$basePath/tmp"]; then
#	mkdir $basePath/tmp
#fi

cd ..
git checkout $2
if [ ! -d "$basePath/$1" ]; then
	mkdir $basePath/$1
fi
cp ../README.md dist/$1/$2.md
git checkout master