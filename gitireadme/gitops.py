import os 

def gitFetch(directory, url):
	'''
		directory: target directory
		url: git fetch url from github
	'''
	if directory != '':
		os.system("cd %s" % os.path.join(os.getcwd(),directory))
	os.system("git init")
	os.system("git remote set-url origin %s" % directory)
	os.system("git fetch origin master")

def gitStore(directory, article_name, commit_id):
	'''
		dir: target directory
		article_name: repository name on github
		commit_id: hashed commit id on github
	'''
	if dir != '':
		basePath = os.path.join(os.getcwd(),directory)
		path = os.path.join(basePath, article_name)
		if not os.path.exists(path):
			os.makedirs(path)
		os.system("cd %s" % os.path.join(basePath))
	os.system("git checkout %s" % commit_id)
	os.system("cp README.md %s/%s/%s.md" % (directory, article_name, commit_id))
	os.system("git checkout master")
