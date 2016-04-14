#!/usr/bin/python -tt
# -*- coding: utf-8 -*-
'''
Created on 2 Mar 2016

@author: aaron
'''
from ubuntu_sso.keyring.pykeyring import USERNAME
from yaml import safe_dump, load
import os,requests, uuid, hashlib, shutil 
import json, codecs, io

GITHUB_API="https://api.github.com/"
CLIENT_ID="0a68d223de982e650c04"
CLIENT_SECRET="399f6072804f110a031c7c67f7a8132700ad3af0"
LANGUGES=["en","zh"]
IDEA_LIST=['idea']

class Idea(object):
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
        # get all forks recursively
        getAllFolks(self, self.raw)
        for fork in self.forks:
            #print fork["name"]
            commits_url = fork["commits_url"].replace("{/sha}","?sha=master")
            print commits_url
            commits = getUrl(commits_url)
            #assume order by time
            print len(commits)
            
            for c in reversed(commits):
                if self.commits.has_key(c["sha"]):
                    continue
                commit = Commit(c,self)
                self.addCommit(commit)
                saveCommitFiles(self.name, c["sha"])
            #add fork to the last commit 
            c = commits[0]
            commit = self.commits[c["sha"]]
            commit.addFolks(fork)
        #get all meta data
        for commit in self.commits.values():
            #set children info 
            for parent in commit.getParents(): 
                parent.addChildren(commit)
            for fork in commit.forks.values():
                meta_datas = getMetaDatas(fork)
                for meta_data in meta_datas:
                    self.addMetaData(meta_data)
                pass
        
    def addMetaData(self,meta_data):       
        if not self.meta_datas.has_key(meta_data["id"]):
            self.meta_datas[meta_data["id"]]=meta_data
        return       
    
    def render(self,out_path):
        out = safe_dump(self.meta_datas.values(),allow_unicode=True) 
        #print out
        f= codecs.open(os.path.join(out_path,self.name+".yml"),"w",encoding="utf-8")
        f.write(out.decode("utf-8"))
        f.close()
        return

def saveCommitFiles(idea_name, commit_id):
    #os.system("mkdir dist"+idea_name+commit_id)
    print commit_id
    os.system("git checkout "+commit_id)
    os.system("mkdir dist/"+idea_name)
    os.system("cp dist/tmp/README.md dist/"+idea_name+"/"+commit_id)

def getMetaDatas(fork):            

    def filterMetaDataFromHtml(html):
        idx = html.find("<!--idea-meta")
        if idx > -1:
            html = html[(idx+13):]
            idx = html.find("-->")
            if idx > -1:
                meta = html[:idx]
                return meta 
            else:
                return None
        else: 
            return None
    meta_datas = []
    for lan in LANGUGES: 
        names = fork["full_name"].split("/")
        prefix = "" if lan == "en" else (lan+"/")# default language is en
        gh_page_url = "http://"+names[0]+".github.io/"+names[1]+"/"+prefix
        r = requests.get(gh_page_url)
        if r.status_code == requests.codes.ok:
            meta_str = filterMetaDataFromHtml(r.text) 
            if meta_str:
                m= hashlib.md5() 
                m.update(meta_str.encode('utf-8'))
                id =m.hexdigest()
                meta_data = load(meta_str) 
                meta_data["id"]=id
                meta_data["language"]=lan
                meta_data["url"]=gh_page_url
                meta_data["fork"]=names[0]
                meta_datas.append(meta_data)
            else:
                continue
        else:
            continue
    return meta_datas

def getAllFolks(idea,fork): 
        idea.forks.append(fork)
        if fork["forks_count"] > 0 :
            forks = getUrl(fork["forks_url"])
            for f in forks:
                getAllFolks(idea, f)

class Commit(object):
    def __init__(self,raw,idea):
        self.raw = raw
        self.id = raw["sha"]
        self.parents ={} 
        self.children = {}
        self.forks = {}
        for p in raw["parents"]:
            parent = idea.commits[p["sha"]] 
            self.parents[parent.id]=parent
        
    def addParent(self,parent):
        if not self.parents.has_key(parent.id):
            self.parents[parent.id]=parent
        return
    def getParents(self):
        return self.parents.values()
    def addChildren(self,child):
        if not self.parents.has_key(child.id):
            self.parents[child.id]=child
        return
    def addFolks(self,fork):
        if not self.forks.has_key(fork["id"]):
            self.forks[fork["id"]]=fork
        return
    def __str__(self):
        return str(self.__unicode__())

    def __unicode__(self):
        return dict(
                id=self.id,
                parents=self.parents,
                forks =self.forks,
                    )

class IdeaCrawler(object):
    '''
    crawl ideas from github user or organization
    '''


    def __init__(self, user_name, path, idea_list):
        '''
        Constructor
        '''
        #self.orgs_name = orgs_name
        self.user_name = user_name
        self.output_path = path
        self.ideas=[]
        #for idea in idea_list:
        #    self.ideas.append(idea)
         
    def crawl(self):
        '''
        for repo in self.ideas:
            idea = Idea(repo)
            idea.crawl()
        '''
        repos = getUserRepo(self.user_name)
        for repo in repos:
            if str(repo["description"]).startswith("unhidea-idea"):
                idea = Idea(repo)
                self.ideas.append(idea)
                idea.crawl()
        

    def render(self):
        #empty output_path
        emptyDirectory(self.output_path)
        for idea in self.ideas:
            idea.render(self.output_path)
            pass

def emptyDirectory(path):                
    for root, dirs, files in os.walk(path):
        for f in files:
            os.unlink(os.path.join(root, f))
        for d in dirs:
            shutil.rmtree(os.path.join(root, d))

def getOrgsRepo(orgs_name):                     
    url = GITHUB_API+"orgs/"+orgs_name+"/repos"        
    return getUrl(url)        

def getUserRepo(user_name):                     
    url = GITHUB_API+"users/"+user_name+"/repos"        
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
    crawler = IdeaCrawler("unhidea", "dist/tmp", IDEA_LIST)
    crawler.crawl()
    crawler.render()