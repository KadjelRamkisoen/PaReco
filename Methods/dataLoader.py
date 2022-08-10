import sys
import time
import re
import json
from datetime import datetime

import Methods.common as common
import Methods.commitLoader as commitloader

try:
    import argparse
    import magic
except ImportError as err:
    print (err)
    sys.exit(-1)

def fetchPrData(source, destination, prs, destination_sha, token_list, ct):
    print('Fetching commit information and files from patches...')
    start = time.time()
    req = 0
    pr_data = {}
    lenTokens = len(token_list)
    
    for k in prs:
        try:
            pr_data[k] = {}

            # Get the PR
            if ct == lenTokens:
                ct = 0
            
            pr_request = 'https://api.github.com/repos/' + source + '/pulls/' + k
            
            pr = commitloader.apiRequest(pr_request, token_list[ct])
            ct += 1
            req += 1

            # Get the commit
            if ct == lenTokens:
                ct = 0
                
            commits_url = pr['commits_url']
            commits = commitloader.apiRequest(commits_url, token_list[ct])
            common.verbose_print(f'ct ={ct}')
            ct += 1
            req += 1

            commits_data = {}

            nr_files = pr['changed_files']

            pr_data[k]['pr_url'] = pr_request
            pr_data[k]['commits_url'] = commits_url
            pr_data[k]['changed_files'] = nr_files
            pr_data[k]['commits_data'] = list()
            pr_data[k]['destination_sha'] = destination_sha

            shas = []
            parents = []
            commits_dates = []

            for i in commits:
                if ct == lenTokens:
                    ct = 0
                commit_url = i['url']
                commit = commitloader.apiRequest(commit_url, token_list[ct])
                ct += 1
                req += 1

                sha = commit['sha']
                if sha not in shas:
                    shas.append(sha)
                    parents.append(commit['parents'][0]['sha'])
                    commits_dates.append(datetime.strptime(commit['commit']['author']['date'], "%Y-%m-%dT%H:%M:%SZ"))

                try:
                    files = commit['files']
                    for j in files:
                        status = j['status']
                        file_name = j['filename']
                        added_lines = j['additions']
                        removed_lines = j['deletions']
                        changes = j['changes']
                        file_ext = commitloader.get_file_type(file_name)
                        if file_name not in commits_data:
                            commits_data[file_name] = list()
                            if ct == lenTokens:
                                ct = 0
                            if commitloader.findFile(file_name, destination, token_list[ct], destination_sha):
                                sub = {}
                                sub['commit_url'] = commit_url
                                sub['commit_sha'] = commit['sha']
                                sub['commit_date'] = commit['commit']['author']['date']
                                sub['parent_sha'] = commit['parents'][0]['sha']
                                sub['status'] =status
                                sub['additions'] = added_lines
                                sub['deletions'] = removed_lines
                                sub['changes'] = changes
                                commits_data[file_name].append(sub)
                            ct += 1
                        else:
                            if ct == lenTokens:
                                ct = 0
                            if commitloader.findFile(file_name, destination, token_list[ct], destination_sha):
                                sub = {}
                                sub['commit_url'] = commit_url
                                sub['commit_sha'] = commit['sha']
                                sub['commit_date'] = commit['commit']['author']['date']
                                sub['parent_sha'] = commit['parents'][0]['sha']
                                sub['status'] =status
                                sub['additions'] = added_lines
                                sub['deletions'] = removed_lines
                                sub['changes'] = changes
                                commits_data[file_name].append(sub)
                            ct += 1
                except Exception as e:
                    print(e)
                    print('This should only happen if there are no files changed in a commit')
            pr_data[k]['commits_data'].append(commits_data)

            min_date = min(commits_dates)
            max_date = max(commits_dates)
            min_index = commits_dates.index(min_date)
            max_index = commits_dates.index(max_date)
            pr_data[k]['first_commit_parent'] = parents[min_index]
            pr_data[k]['last_commit_sha'] = shas[max_index]
            
        except Exception as e:
            print('An error occurred while fetching the pull request information from GitHub.')
            print(pr_request)
            print (f'Error has to do with: {e}')

    end = time.time()
    runtime = end - start
    print('Fetch Runtime: ', runtime)
    
    return ct, pr_data, req, runtime

def getDestinationSha(destination, cut_off_date, token_list, ct):
    destination_sha = ''
    lenTokens = len(token_list)
    if ct == lenTokens:
        ct = 0
    cut_off_commits = commitloader.apiRequest('https://api.github.com/repos/' + destination +'/commits?until=' + cut_off_date, token_list[ct])
    ct += 1
    
    destination_sha = cut_off_commits[0]['sha']
    return destination_sha, ct

def removeComments(source, fileExt):
    if fileExt == common.FileExt.C or fileExt == common.FileExt.Java:
        norm_lines = []
        for c in common.c_regex.finditer(source):
            if c.group('noncomment'):
                norm_lines.append(c.group('noncomment'))
            elif c.group('multilinecomment'):
                newlines_cnt = c.group('multilinecomment').count('\n')
                while newlines_cnt:
                    norm_lines.append('\n')
                    newlines_cnt -= 1
        source = ''.join(norm_lines)
    elif fileExt == common.FileExt.Python:
        # print(source)
        # norm_lines = []
        # for c in common.py_regex.finditer(source):
        #     if c.group('noncomment'):
        #         norm_lines.append(c.group('noncomment'))
        #     elif c.group('multilinecomment'):
        #         newlines_cnt = c.group('multilinecomment').count('\n')
        #         while newlines_cnt:
        #             norm_lines.append('\n')
        #             newlines_cnt -= 1
        source = ''.join([c.group('noncomment') for c in common.py_regex.finditer(source) if c.group('noncomment')])
        source = ''.join(
            [c.group('noncomment') for c in common.py_multiline_1_regex.finditer(source) if c.group('noncomment')])
        source = ''.join(
            [c.group('noncomment') for c in common.py_multiline_2_regex.finditer(source) if c.group('noncomment')])
    elif fileExt == common.FileExt.ShellScript:
        source = ''.join(
            [c.group('noncomment') for c in common.shellscript_regex.finditer(source) if c.group('noncomment')])
    elif fileExt == common.FileExt.Perl:
        source = ''.join([c.group('noncomment') for c in common.perl_regex.finditer(source) if c.group('noncomment')])
    elif fileExt == common.FileExt.PHP:
        norm_lines = []
        for c in common.php_regex.finditer(source):
            if c.group('noncomment'):
                norm_lines.append(c.group('noncomment'))
            elif c.group('multilinecomment'):
                newlines_cnt = c.group('multilinecomment').count('\n')
                while newlines_cnt:
                    norm_lines.append('\n')
                    newlines_cnt -= 1
        source = ''.join(norm_lines)
    elif fileExt == common.FileExt.Ruby or fileExt == common.FileExt.GEMFILE:
        norm_lines = []
        for c in common.ruby_regex.finditer(source):
            if c.group('noncomment'):
                norm_lines.append(c.group('noncomment'))
            elif c.group('multilinecomment'):
                newlines_cnt = c.group('multilinecomment').count('\n')
                while newlines_cnt:
                    norm_lines.append('\n')
                    newlines_cnt -= 1
        source = ''.join(norm_lines)
    elif fileExt in [common.FileExt.scala, common.FileExt.js, common.FileExt.kotlin, common.FileExt.gradle]:
        source = ''.join([c.group('noncomment') for c in common.js_regex.finditer(source) if c.group('noncomment')])
        source = ''.join(
            [c.group('noncomment') for c in common.js_partial_comment_regex.finditer(source) if c.group('noncomment')])
    elif fileExt == common.FileExt.yaml:
        source = ''.join([c.group('noncomment') for c in common.yaml_regex.finditer(source) if c.group('noncomment')])
        source = re.sub(common.yaml_double_quote_regex, "", source)
        source = re.sub(common.yaml_single_quote_regex, "", source)
    elif fileExt == common.FileExt.ipynb:
        json_data = json.loads(source)
        python_code = ""

        for i in json_data['cells']:
            for j in i['source']:
                if j.endswith('\n'):
                    python_code += j
                else:
                    python_code += j + '\n'

        source = ''.join([c.group('noncomment') for c in common.py_regex.finditer(python_code) if c.group('noncomment')])
        source = ''.join(
            [c.group('noncomment') for c in common.py_multiline_1_regex.finditer(source) if c.group('noncomment')])
        source = ''.join(
            [c.group('noncomment') for c in common.py_multiline_2_regex.finditer(source) if c.group('noncomment')])
        
    elif fileExt == common.FileExt.JSON:
        source = common.whitespaces_regex.sub("", source)
        source = source.lower()
#         source = source.split()
        
    elif fileExt == common.FileExt.xml:
        source = ''.join([c.group('noncomment') for c in common.xml_regex.finditer(source) if c.group('noncomment')])
    return source
