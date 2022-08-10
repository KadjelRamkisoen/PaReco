import os
import requests
import difflib
from datetime import datetime

import Methods.common as common
import Methods.patchLoader as patchloader
import Methods.dataLoader as dataloader
import Methods.sourceLoader as sourceloader
import Methods.commitLoader as commitloader

"""
    unified_diff
    To create a unified diff file
    
    @before - The state of the file before changes
    @after - The state of the file after the changes
"""
def unified_diff(before, after):
    file1 = open(before).readlines()
    file2 = open(after).readlines()

    delta = difflib.unified_diff(file1, file2)
                      
    file =list()
    for line in delta:
#         if not line.startswith('---') or not line.startswith('+++'):
        file.append(line)
    return file

"""
    save_patch
    To save a patch file
    
    @storageDir - The directory where to save the patch
    @fileName - The name of the file
    @file - The content of the file
"""
def save_patch(storageDir, fileName, file, dup_count):
    patch_path = ''
    if not os.path.exists(storageDir):
        os.makedirs(storageDir)
        patch_path = storageDir + fileName + '.patch'
        f = open(patch_path, 'x')
        for line in file[2:]:
            f.write(line)
        f.close()
        
    else:
        if not os.path.isfile(storageDir + fileName):
            patch_path = storageDir + fileName + '.patch'
            f = open(patch_path, 'w')
            for line in file[2:]:
                f.write(line)
            f.close()
        else:
            patch_path = storageDir + fileName+ '_' + dup_count + '.patch'
            f = open(patch_path, 'w')
            for line in file[2:]:
                f.write(line)
            f.close()
            dup_count += 1
    return patch_path, dup_count
        
"""
    processPatch
    To process a patch
    This is done before bein able to classify the patch
    
    @patchPath - the path where the patch file is stored
    @dstPath - the path where the destination file is stored
    @typePatch - the kind of patch we are dealing with, buggy or fixed
"""
def processPatch(patchPath, dstPath, typePatch, fileExt):
    # reset ngram_size to 4
    common.ngram_size = 4
    
    patch = patchloader.PatchLoader()
    npatch = patch.traverse(patchPath, typePatch, fileExt)

    source = sourceloader.SourceLoader()
    nmatch = source.traverse(dstPath, patch, fileExt)

    # reset ngram_size to 4
#     common.ngram_size = 4

    return patch, source

"""
    apiRequest
    To make api requests to the GitHub API
    
    @url - the url for the API
    @token - GitHub API token
"""
def apiRequest(url, token):
    header = {'Authorization': 'token %s' % token}
    response = requests.get(url, headers=header)
    return response

"""
    get_ext
    Extract the extension of the a file
    
    @file - the file from which to extract the file
"""
def get_ext(file):
    ext = file.split['.'][-1]

"""
    getFileBeforePatch
    Extracts the buggy file using the GitHub API
    
    @repo_dir - directory where to store the file
    @mainline - the source repository
    @sha - the commit sha-value that last changed the file
    @parent - the parent commit sha-value of the commit that last changed the file
    @pr_nr - the pull request number of the patch
    @file - the file path in the repository
    @fileDir - the sub directory where to store the file
    @fileName - a name to store the file
    @token - token needed for the GitHub API
"""
def getFileBeforePatch(repo_dir, mainline, sha, parent, pair_nr, pr_nr, file, fileDir, fileName, fileExt, token):
    fileBeforePatchDir = repo_dir + str(pair_nr) + '/' + mainline + '/' + str(pr_nr) + '/' + sha + '/before_patch/' + fileDir
    beforePatch_url = 'https://raw.githubusercontent.com/' + mainline + '/' + parent + '/' + file
    fileBeforePatch = apiRequest(beforePatch_url, token)

    normFile = dataloader.removeComments(fileBeforePatch.content.decode(), fileExt)
    commitloader.saveFile(normFile, fileBeforePatchDir, fileName)
    return fileBeforePatchDir + fileName, beforePatch_url

def getFileAfterPatch(repo_dir, mainline, sha, pair_nr, pr_nr, file, fileDir, fileName, fileExt, token):
    fileAfterPatchDir = repo_dir + str(pair_nr) + '/' + mainline + '/' + str(pr_nr) + '/' + sha + '/after_patch/' + fileDir
    fileAfterPatchUrl = 'https://raw.githubusercontent.com/' + mainline + '/' + sha + '/' + file
    fileAfterPatch = apiRequest(fileAfterPatchUrl, token)

    normFile =dataloader.removeComments(fileAfterPatch.content.decode(), fileExt)
    commitloader.saveFile(normFile, fileAfterPatchDir, fileName)
    return fileAfterPatchDir + fileName, fileAfterPatchUrl

def getFileFromDest(repo_dir, variant, sha, pair_nr, file, fileDir, fileName, fileExt, token):
    destPath = repo_dir + str(pair_nr) + '/' + variant +  '/' + fileDir
    if not os.path.exists(destPath):
        os.makedirs(destPath)
    dest_url = "https://raw.githubusercontent.com/" + variant + "/" + sha + "/" + file
    destFile = apiRequest(dest_url, token)

    normFile = dataloader.removeComments(destFile.content.decode(), fileExt)
    commitloader.saveFile(normFile, destPath, fileName)
    return destPath + fileName, dest_url
    
def calcMatchPercentage(results, hashes):
    matched_code = []
    not_matched = []
    total = 0
    matched = 0

    for h in results:
        total += 1
        if results[h]['True']:
            matched += 1
            matched_code.append(hashes[h])
        else:
            not_matched.append(hashes[h])
    if total!= 0:
        return ((matched/total)*100)
    else:
        return 0

"""
    find_hunk_matches
    To find the different matches between two hunk using the hashed values
    
    @match_items
    @_type
    @important_hashes
    @source_hashes
"""
def find_hunk_matches(match_items, _type):
    seq_matches = {} 

    for patch_nr in match_items:
        seq_matches[patch_nr] = {}
        seq_matches[patch_nr]['sequences'] = {}
        seq_matches[patch_nr]['class'] = ''
        for patch_seq in match_items[patch_nr]:

            seq_matches[patch_nr]['sequences'][patch_seq] = {}
            seq_matches[patch_nr]['sequences'][patch_seq]['count'] = 0
            seq_matches[patch_nr]['sequences'][patch_seq]['hash_list'] = list(match_items[patch_nr][patch_seq].keys())
            
            for k in match_items[patch_nr][patch_seq]:
                if match_items[patch_nr][patch_seq][k]:
                    seq_matches[patch_nr]['sequences'][patch_seq]['count'] += 1
    
    match_bool = True

    for seq_nr in seq_matches:
        for seq in seq_matches[seq_nr]['sequences']:
            if seq_matches[seq_nr]['sequences'][seq]['count'] < 2:
                match_bool = False
                break
        _class = ''
        
        if _type == 'MO':
            if match_bool:
                _class = _type
            else:
                _class = 'MC'
        elif _type == 'ED':
            if match_bool:
                _class = _type
            else:
                _class = 'MC'
                
        seq_matches[seq_nr]['class']= _class        
    
    return seq_matches

"""
    classify_hunk
    To classify a hunk
    
    @class_patch
    @class_buggy
"""
def classify_hunk(class_buggy, class_patch):
    
    finalClass = ''
    if class_buggy == 'MO' and class_patch =='ED':
        finalClass = 'SP'
        
    if class_buggy == 'MO' and class_patch == 'MC':
        finalClass = 'MO'
        
    if class_buggy == 'MC' and class_patch == 'ED':
        finalClass = 'ED'
        
    if class_buggy == 'MC' and class_patch == 'MC':
        finalClass = 'NA'
        
    if class_patch == '' and class_buggy !='':
        finalClass = class_buggy
        
    if class_patch != '' and class_buggy =='':
        finalClass = class_patch
        
    if class_patch == '' and class_buggy =='':
        finalClass = 'NA'
        
    return finalClass

"""
    classify_patch
    To classify a patch based on the hunks
    
    @hunk_classifications - the classifications for the different hunks in the .diff of a file changed in a PR
"""
def classify_patch(hunk_classifications):
    NA_total = 0
    MO_total = 0
    ED_total = 0
    SP_total = 0
    
    finalClass= ''
    for i in range(len(hunk_classifications)):
        if hunk_classifications[i] =='ED':
            ED_total += 1
        elif hunk_classifications[i] =='MO':
            MO_total += 1
        elif hunk_classifications[i] =='NA':
            NA_total += 1
        elif hunk_classifications[i] =='SP':
            SP_total += 1
    
    if MO_total == 0 and ED_total == 0 and SP_total ==0:
        max_total = NA_total
        finalClass = 'NA'
    else:
        max_total = ED_total
        finalClass='ED'
        
        if max_total < MO_total:
            max_total = MO_total
            finalClass = 'MO'
        elif max_total == MO_total:
            # Possible SPLIT case if ED == MO
            finalClass='SP'
            
        if max_total <= SP_total:
            max_total = SP_total
            finalClass = 'SP'
            
    return finalClass

"""
    find_hunk_matches_w_important_hash
    To find the different matches between two hunk using the hashed values and using the important hash feature
    
    @match_items
    @_type
    @important_hashes
    @source_hashes
"""
def find_hunk_matches_w_important_hash(match_items, _type, important_hashes, source_hashes, patch_list):
    seq_matches = {}
    test = []
    # print(f'important hashes (+/- lines from patch): \n {important_hashes} \n')
    # print(f'source hashes: \n {source_hashes} \n')
    for lines in important_hashes:
        for line in lines:
            for each in line:
                for ngram, hash_list in source_hashes:
                    if each in ngram:
                        test.append(hash_list)

    # print(f'TEST: \n {test} \n')

    # print(f'Match items: \n {match_items} \n')

    found_important_hashes = {}
    important_hash_match = 0
    total_important_hashes = len(important_hashes)
    for patch_nr in match_items:
        patch_important = []
        for lines in important_hashes:
            for line in lines:
                for each in line:
                    for ngram, hash_list in patch_list[patch_nr][5]:
                        if each in ngram:
                            patch_important.append(hash_list)

        seq_matches[patch_nr] = {}
        seq_matches[patch_nr]['sequences'] = {}
        seq_matches[patch_nr]['class'] = ''
        for patch_seq in match_items[patch_nr]:
            seq_matches[patch_nr]['sequences'][patch_seq] = {}
            seq_matches[patch_nr]['sequences'][patch_seq]['count'] = 0
            seq_matches[patch_nr]['sequences'][patch_seq]['hash_list'] = list(match_items[patch_nr][patch_seq].keys())

            if seq_matches[patch_nr]['sequences'][patch_seq]['hash_list'] in patch_important:
                seq_matches[patch_nr]['sequences'][patch_seq]['important'] = True
                important_hash_match =+ 1
            else:
                seq_matches[patch_nr]['sequences'][patch_seq]['important'] = False

            for k in match_items[patch_nr][patch_seq]:
                if match_items[patch_nr][patch_seq][k]:
                    seq_matches[patch_nr]['sequences'][patch_seq]['count'] += 1

    # if total_important_hashes != 0:
    #     important_hash_perc = (important_hash_match*100)/total_important_hashes
    
    for i in seq_matches:
        if test:
            match_bool = False
        else:
            match_bool = True
#         print(f'match bool before = {match_bool}')

#         print(f'i = {i}')
#         print(f"seq_matches[i] = {seq_matches[i]}")
        for j in seq_matches[i]['sequences']:
#             print(f'j = {j}')
            if test:
#                 print(f"seq_matches[i]['sequences'][j] = {seq_matches[i]['sequences'][j]}")
#                 print(f"test=TRUE -> {seq_matches[i]['sequences'][j]['important']}")
                if seq_matches[i]['sequences'][j]['important']:
                    if seq_matches[i]['sequences'][j]['count'] != 0:
#                         print(f'test=TRUE -> count!=0')
                        match_bool = True
                    else:
#                         print(f'test=TRUE -> count==0')
                        match_bool = False
                        break
                else:
#                     print(f'test=TRUE -> important=FALSE')
                    if seq_matches[i]['sequences'][j]['count'] >= 2:
                        match_bool = True
                    elif seq_matches[i]['sequences'][j]['count'] < 2:
#                         print(f'test=TRUE -> important=FALSE&count<2')
                        match_bool = False
                        break

            else:
#                 print(f'test=FALSE')
                if seq_matches[i]['sequences'][j]['count'] < 2:
#                     print(f'test=FALSE -> count<2')
                    match_bool = False
                    break

#         print(f'match bool after = {match_bool}')
        _class = ''

        if _type == 'MO':
            if match_bool:
                _class = _type
            else:
                _class = 'MC'

        elif _type == 'ED':
            if match_bool:
                _class = _type
            else:
                _class = 'MC'
                 
#         print(f'Class = {_class}\n\n================================================================================')
        seq_matches[i]['class']= _class 
#     print(f'DONE ================================================================================ DONE')
    return seq_matches 

"""
    getFirstLastCommit
    Retrieve the first and the last commit of a pull request
    
    @pr_commits
"""
def getStatus(file_commits):
    first_commit = {}
    for commit in file_commits:
        first_commit_date = ''
        commit_date = commit['commit_date']
        if first_commit_date == '':
            first_commit_date = commit_date
            first_commit = commit
        else:
            if commit_date < first_commit_date:
                first_commit_date = commit_date
                first_commit = commit

    return first_commit['status']

    # shas = []
    # dates = []
    # commits = []
    # for files in pr_commits:
    #     for f in files:
    #         for commit in files[f]:
    #             # commit_date = commit['commit_date']
    #             sha = commit['commit_sha']
    #             if sha not in shas:
    #                 shas.append(sha)
    #                 commits.append(commit)
    #                 dates.append(datetime.strptime(commit['commit_date'], "%Y-%m-%dT%H:%M:%SZ"))
    #
    # min_date = min(dates)
    #
    # min_index = dates.index(min_date)
    #
    # return commits[min_index]['status']
                # if first_commit_date == '':
                #     first_commit_date = commit_date
                #     first_commit = commit
                # else:
                #     if commit_date < first_commit_date:
                #         first_commit_date = commit_date
                #         first_commit = commit
                #     if last_commit_date == '':
                #         last_commit_date = commit_date
                #         last_commit = commit
                #     else:
                #         if commit_date > last_commit_date:
                #             last_commit_date = commit_date
                #             last_commit = commit
    # return first_commit, last_commit