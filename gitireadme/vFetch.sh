# store every version of an article

basePath=dist
#if [! -d "$basePath/tmp"]; then
#	mkdir $basePath/tmp
#fi

cd ..
git init
echo "git remote set-url origin $1"
git remote set-url origin $1
git fetch origin master
