#!/usr/bin/python -tt
# -*- coding: utf-8 -*-
'''
Created on 2 Mar 2016

@author: aaron
'''
from ubuntu_sso.keyring.pykeyring import USERNAME
from yaml import safe_dump, load
import sys, os,requests, uuid, hashlib, shutil 
import json, codecs, io
from subprocess import Popen
import gitops

GITHUB_API="https://api.github.com/"
GITHUB='https://github.com/'
CLIENT_ID="0a68d223de982e650c04"
CLIENT_SECRET="399f6072804f110a031c7c67f7a8132700ad3af0"
LANGUGES=["en","zh"]
IDEA_LIST=['article']

class User(object):
    def __init__(self, raw, repo_name):
        self.raw = raw
        self.id = raw['owner']['id']
        self.name = raw['full_name']
        self.description = raw['description']
        self.repo_name = repo_name

    def addInfo(self):
        self.stars = self.raw['stargazers_count']
        self.watches = self.raw['watchers_count']
        return

    def addParent(self, parent):
        self.parent = parent
        return

    def __str__(self):
        return str(self.__unicode__())

    def __repr__(self):
        return self.__unicode__()

    def __unicode__(self):
        return dict(userId=self.id,
                name=self.name,
                description=self.description,
                parent=self.parent,
                stars=self.stars,
                watches=self.watches,
                )


class Article(object):
    def __init__(self,raw):
        self.raw = raw
        self.name = raw['name']
        self.commits = {} 
        self.forks = []
        self.meta_datas = {}
        self.users = {}
        self.parent = {}
        self.branches = {}

    def addCommit(self,commit): 
        if not self.commits.has_key(commit.id):
            self.commits[commit.id]=commit
        return
    
    def addUser(self, user):
        if not self.users.has_key(user.id):
            self.users[user.id] = user
        return

    def crawl(self):
        # get the root repository
        root = getRoot(self.raw)
        # get all forks recursively
        getAllFolks(self, root)
        for fork in self.forks:
            print fork["forks_url"]
            user = User(fork, self.name)
            if self.parent.has_key(user.id):
                parent = self.parent[user.id]
            else:
                parent = ''
            print parent
            self.addUser(user)
            user.addInfo()
            user.addParent(parent)
            getAllBranches(self, fork)

            for branch in self.branches[fork['owner']['login']].values():
                print branch
                tmp_url = '?sha='+branch['name']
                commits_url = fork["commits_url"].replace("{/sha}",tmp_url)
                print commits_url
                commits = getUrl(commits_url)
                #assume order by time

                url = GITHUB+fork['owner']['login']+'/'+self.name+'.git'
                gitops.gitFetch('dist', url)

                for c in reversed(commits):
                    if self.commits.has_key(c["sha"]):
                        continue
                    commit = Commit(c,self)
                    self.addCommit(commit)

                #add fork to the last commit 
                c = commits[0]
                commit = self.commits[c["sha"]]
                commit.addFolks(fork)
                commit.addBranch(branch, user.id)
                if not os.path.exists(os.path.join(os.getcwd(),'dist',self.name,c["sha"]+'.md')):
                        print os.path.join('dist',self.name,c["sha"]+'.md')
                        gitops.gitStore('dist',self.name, c['sha'])
            
        #set commit children
        for commit in self.commits.values():
            for parent in commit.getParents(): 
                parent.addChildren(commit)


    def render_yaml(self,out_path):
        f = codecs.open(os.path.join(out_path,self.name+".yml"),"w",encoding="utf-8")
        commits = [c.__repr__() for c in self.commits.values()]
        users = [u.__repr__() for u in self.users.values()]
        meta = dict(commits=commits, forks=users)
        out = safe_dump(meta,allow_unicode=True)
        f.write(out.decode("utf-8"))
        f.close()
        return

    def render_json(self, out_path):
        f = codecs.open(os.path.join(out_path,self.name+".json"),"w",encoding="utf-8")
        commits = [c.__repr__() for c in self.commits.values()] 
        users = [u.__repr__() for u in self.users.values()]
        meta = dict(commits=commits, forks=users)
        out = json.dumps(meta)
        f.write(out.decode("utf-8"))
        f.close()
        return

def fetchCommitFiles(url):
    print 'fetching...'
    Popen('./script/vFetch.sh %s' % (url,), shell=True)

def saveCommitFiles(article_name, commit_id):
    # run shell script vStore.sh
    print 'saving...'
    print article_name, commit_id
    Popen('./script/vStore.sh %s %s' % (article_name, commit_id,), shell=True)

def getAllBranches(article, fork):
    url = GITHUB_API+'repos/'+fork['full_name']+'/branches'
    branches = getUrl(url)
    for branch in branches:
        owner = fork['owner']['login']
        if not article.branches.has_key(owner):
            article.branches[owner] = {}
        article.branches[owner][branch['name']] = branch

def getAllFolks(article,fork): 
    article.forks.append(fork)
    if fork["forks_count"] > 0 :
        url = fork['forks_url']
        forks = getUrl(url)
        for f in forks:
            getParent(article, f, url)
            getAllFolks(article, f)

def getParent(article, fork, url):
    url = filter(None, url.split('/'))
    parent = url[len(url)-3]
    print parent, fork['owner']['login']
    if not article.parent.has_key(fork['owner']['id']):
        article.parent[fork['owner']['id']] = parent

def getRoot(raw):
    if raw['fork'] == True:
        return raw['source']
    else:
        return raw

class Commit(object):
    def __init__(self, raw, article):
        self.raw = raw
        self.id = raw["sha"]
        self.parents ={} 
        self.children = {}
        self.forks = {}
        self.branches = {}
        for p in raw["parents"]:
            parent = article.commits[p["sha"]] 
            self.parents[parent.id]=parent
        
    def getParents(self):
        return self.parents.values()
    def getParentsIds(self):
        parents=self.getParents()
        return [p.id for p in parents]
    def getBranchesNames(self):
        forks = self.forks.values()
        return [f["full_name"]+'/'+self.branches[f['owner']['id']]['name'] for f in forks]
    def addChildren(self,child):
        if not self.children.has_key(child.id):
            self.children[child.id]=child
        return
    def addFolks(self,fork):
        if not self.forks.has_key(fork["id"]):
            self.forks[fork["id"]]=fork
        return
    def addBranch(self, branch, user_id):
        if not self.branches.has_key(user_id):
            self.branches[user_id]=branch
        return
    def __str__(self):
        return str(self.__unicode__())
    
    def __repr__(self):
        return self.__unicode__()

    def __unicode__(self):
        return dict(
                id=self.id,
                parents=self.getParentsIds(),
                branches=self.getBranchesNames(),
                username=self.raw["commit"]["author"]["name"],
                date=self.raw["commit"]["author"]["date"],
                    )

class ArticleSpider(object):
    '''
    crawl articles from github user or organization
    '''


    def __init__(self, repository_url, output_path):
        '''
        Constructor
        '''
        self.output_path = output_path
        self.repository_url = repository_url
         
    def crawl(self):
        repository_info = getRepo(self.repository_url)
        #print repository_info
        self.article = Article(repository_info)
        self.article.crawl()
        

    def render(self):
        #empty output_path
        emptyDirectory(self.output_path)
        self.article.render_yaml(self.output_path)
        self.article.render_json(self.output_path)

def emptyDirectory(path):                
    os.system("rm -rf dist/%s/*" % path)

def getOrgsRepo(orgs_name):                     
    url = GITHUB_API+"orgs/"+orgs_name+"/repos"        
    return getUrl(url)        

def getRepo(repository):                     
    url = GITHUB_API+"repos/"+repository        
    return getUrl(url)        

def getUrl(url):
    if url.find("?")== -1:
        url+="?1=1"
    url+="&client_id="+CLIENT_ID+"&client_secret="+CLIENT_SECRET
    r = requests.get(url)
    if not r.status_code == 200:
        print "error return code", r.status_code
        return None
    else:
        return r.json()
 
if __name__ == "__main__":
    if not os.path.exists(os.path.join(os.getcwd(),'dist')):
        os.makedirs('dist')
    if not os.path.exists(os.path.join(os.getcwd(),'dist/srcfile')):
        os.makedirs('dist/srcfile')
    repository_url = sys.argv[1]
    #print repository_url
    spider = ArticleSpider(repository_url, "dist/srcfile")
    spider.crawl()
    spider.render()
    
