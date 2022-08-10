import os
import requests
import csv
import json
import sys
import re
import time
from collections import defaultdict
import bitarray
import re
import time
import mimetypes
    
import Methods.common as common
import Methods.patchLoader as patchloader
import Methods.sourceLoader as sourceloader

try:
    import argparse
    import magic
except ImportError as err:
    print (err)
    sys.exit(-1)

"""
    apiRequest(url)
    
    @url - the url for the request
"""
def apiRequest(url, token):
    header = {'Authorization': 'token %s' % token}
    response = requests.get(url, headers=header)
    jsonResponse = json.loads(response.content)
    return jsonResponse

"""
    getCommitsAhead(mainline, fork)
    
    Get the commits that the mainline is ahead of the variant
    
    @mainline - the mainline author/repo
    @fork - the fork author/repo 
    @commitToken - the token used for constructin the compareUrl
    @compareToken - the token used for comparing mainline and fork
"""
def getCommitsAhead(mainline, fork, commitToken, compareToken):  
    compareUrl = "https://api.github.com/repos/" + fork + "/compare/master" + "..." + mainline.split('/')[0] + ":master" \
        + "?access_token=" + compareToken

    jsonCommits = apiRequest(compareUrl)

    return jsonCommits["commits"]

"""
    getCommitFiles(commits, getCommitToken)
    
    Get the files for each commit
    
    @commits - the commits for which files need to be retrieved
    @getCommitToken - the token used for the qpi reqiest to get the commit
    
    commitFilesDict={
        "sha": {
            "commitUrl": url
            "files": list(file 1, file 2, ... , file n)
        }
        
    }
"""
def getCommit(commit, getCommitToken):
    sha = commit["sha"]
    commitUrl = commit['url']

    commitFilesDict[sha] = {}
    commitFilesDict[sha]["commitUrl"] = commitUrl
    commitFilesDict[sha]["files"] = list()

    commit = apiRequest(commitUrl + "?access_token=" + getCommitToken)

    return commit

"""
    findFile(filename, repo)
    
    Check if the file exists in the other repository
    
    @filename - the file path to be checked for existence
    @repo - the repository in which the existence of the file must be checked
    @checkFileExistsToken - the token for the api request
"""
def findFile(filename, repo, token, sha):
    requestUrl = "https://api.github.com/repos/" + repo + "/contents/" + filename + '?ref=' + sha
    response = apiRequest(requestUrl,token) 
    path = ''
    try:
        path = response['path']
        return True
    except Exception as e:
        return False

"""
    fileName(name)
    
    Extract the file name used for storing the file
    
    @name - the patch retrieved from the commit api for the file
"""
def fileName(name):
    if name.startswith('.'):
        if '/' in name:
            return(name.split('/')[-1])
        return (name[1:])
    elif '/' in name:
        return(name.split('/')[-1])
    elif '/' not in name:
        return(name)
    else: 
        sys.exit(1)
    
def fileDir(name):
    if name.startswith('.'):
        return ''
    elif '/' in name:
        return(name.split('/')[:-1])
    elif '/' not in name:
        return ''
    else: 
        sys.exit(1)
    
"""
    get_patch(url, token)
    
    Send a request to the github api to find retrieve the patch of a commit and saves it to a .patch file
    
    @url - the url for the request that will be send to GitHub
    @token - the authentication tolen that will be used in the request
"""
def getPatch(file, storageDir, fileName):
    if not os.path.exists(storageDir):
        os.makedirs(storageDir)
        f = open(storageDir + fileName, 'w')
        f.write(file)
        f.close()
    else:
        f = open(storageDir + fileName, 'w')
        f.write(file)
        f.close()

def saveFile(file, storageDir, fileName): 
    if not os.path.exists(storageDir):
        os.makedirs(storageDir)
        f = open(storageDir + fileName, 'x')
        f.write(file)
        f.close()
    else:
        f = open(storageDir + fileName, 'w')
        f.write(file)
        f.close()

def get_file_type(file_path):
    '''
    Guess a file type based upon a file extension (mimetypes module)
    '''
    name = fileName(file_path)
    if name.lower() == 'requirements.txt' or name.lower() == 'requirement.txt':
        file_ext = common.FileExt.REQ_TXT
    else:
        ext = file_path.split('.')[-1]
        file_ext = None
        if ext == 'c' or ext == 'h' or ext == 'cpp':
            file_ext = common.FileExt.C
        elif ext == 'java':
            file_ext = common.FileExt.Java
        elif ext == 'sh':
            file_ext = common.FileExt.ShellScript
        elif ext == 'pl':
            file_ext = common.FileExt.Perl
        elif ext == 'py':
            file_ext = common.FileExt.Python
        elif ext == 'php':
            file_ext = common.FileExt.PHP
        elif ext == 'rb':
            file_ext = common.FileExt.Ruby
        elif ext == 'js':
            file_ext = common.FileExt.js
        elif ext == 'scala':
            file_ext = common.FileExt.scala
        elif ext == 'yaml' or ext == 'yml':
            file_ext = common.FileExt.yaml
        elif ext == 'ipynb':
            file_ext = common.FileExt.ipynb
        elif ext == 'json':
            file_ext = common.FileExt.JSON
        elif ext == 'kt':
            file_ext = common.FileExt.kotlin
        elif ext == 'gradle':
            file_ext = common.FileExt.gradle
        elif ext == 'gemfile':
            file_ext = common.FileExt.GEMFILE    
        elif ext == 'xml':
            file_ext = common.FileExt.xml
        else:
            file_ext = common.FileExt.Text

    return file_ext