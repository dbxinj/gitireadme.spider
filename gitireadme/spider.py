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

GITHUB_API="https://api.github.com/"
GITHUB='https://github.com/'
CLIENT_ID="0a68d223de982e650c04"
CLIENT_SECRET="399f6072804f110a031c7c67f7a8132700ad3af0"
LANGUGES=["en","zh"]
IDEA_LIST=['article']

class Article(object):
    def __init__(self,raw):
        self.raw = raw
        self.name = raw['name']
        self.commits = {} 
        self.forks =[]
        self.meta_datas={}

    def addCommit(self,commit): 
        if not self.commits.has_key(commit.id):
            self.commits[commit.id]=commit
        return
        
    def crawl(self):
        # get the root repository
        root = getRoot(self.raw)
        # get all forks recursively
        getAllFolks(self, root)
        print 'forks:', len(self.forks)
        for fork in self.forks:
            #print fork["name"]
            commits_url = fork["commits_url"].replace("{/sha}","?sha=master")
            print commits_url
            commits = getUrl(commits_url)
            #assume order by time

            print 'commits:', len(commits)
            print fork['owner']['login']
            url = GITHUB+fork['owner']['login']+'/'+self.name+'.git'
            fetchCommitFiles(url)

            for c in reversed(commits):
                if self.commits.has_key(c["sha"]):
                    continue
                commit = Commit(c,self)
                self.addCommit(commit)
            #add fork to the last commit 
            c = commits[0]
            commit = self.commits[c["sha"]]
            commit.addFolks(fork)
            if not os.path.exists(os.path.join(os.getcwd(),'dist',self.name,c["sha"]+'.md')):
                    print os.path.join('dist',self.name,c["sha"]+'.md')
                    saveCommitFiles(self.name, c["sha"])
            
        #set commit children
        for commit in self.commits.values():
            for parent in commit.getParents(): 
                parent.addChildren(commit)
    
    def render(self,out_path):
        commits = [c.__repr__() for c in self.commits.values()]
        out = safe_dump(commits,allow_unicode=True) 
        #print out
        f= codecs.open(os.path.join(out_path,self.name+".yml"),"w",encoding="utf-8")
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

def getAllFolks(article,fork): 
    article.forks.append(fork)
    if fork["forks_count"] > 0 :
        forks = getUrl(fork["forks_url"])
        for f in forks:
            getAllFolks(article, f)

def getRoot(raw):
    if raw['fork'] == True:
        return raw['source']
    else:
        return raw

class Commit(object):
    def __init__(self,raw,article):
        self.raw = raw
        self.id = raw["sha"]
        self.parents ={} 
        self.children = {}
        self.forks = {}
        for p in raw["parents"]:
            parent = article.commits[p["sha"]] 
            self.parents[parent.id]=parent
        
    def getParents(self):
        return self.parents.values()
    def getParentsIds(self):
        parents=self.getParents()
        return [p.id for p in parents]
    def getForksNames(self):
        forks = self.forks.values()
        return [f["name"] for f in forks]
    def addChildren(self,child):
        if not self.children.has_key(child.id):
            self.children[child.id]=child
        return
    def addFolks(self,fork):
        if not self.forks.has_key(fork["id"]):
            self.forks[fork["id"]]=fork
        return
    def __str__(self):
        return str(self.__unicode__())
    
    def __repr__(self):
        return self.__unicode__()

    def __unicode__(self):
        return dict(
                id=self.id,
                parents=self.getParentsIds(),
                forks =self.getForksNames(),
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
        '''
        for repo in self.articles:
            article = Article(repo)
            article.crawl()
        '''
        repository_info = getRepo(self.repository_url)
        #print repository_info
        self.article = Article(repository_info)
        self.article.crawl()
        

    def render(self):
        #empty output_path
        emptyDirectory(self.output_path)
        self.article.render(self.output_path)

def emptyDirectory(path):                
    for root, dirs, files in os.walk(path):
        for f in files:
            os.unlink(os.path.join(root, f))
        for d in dirs:
            shutil.rmtree(os.path.join(root, d))

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
    if not os.path.exists(os.path.join(os.getcwd(),'dist/tmp')):
        os.makedirs('dist/tmp')
    repository_url = sys.argv[1]
    #print repository_url
    spider = ArticleSpider(repository_url, "dist/tmp")
    spider.crawl()
    spider.render()
    
