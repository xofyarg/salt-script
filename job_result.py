#!/usr/bin/env python

import os
import os.path
import sys

import salt.config
import salt.runner

# how many times will try to get the result
RETRY = -1
# salt master's config path
CONFIG = '/etc/salt/master'

def main():
    global RETRY, CONFIG

    if len(sys.argv) < 2:
        print 'Usage: %s <jid>' % sys.argv[0]
        sys.exit(1)

    jid = sys.argv[1]
    print 'using master config file: %s' % CONFIG
    if not os.path.isfile(CONFIG):
        print 'cannot find master config file: %s' % CONFIG
        sys.exit(1)

    __opts__ = salt.config.master_config(CONFIG)
    runner = salt.runner.Runner(__opts__)

    # backup stdout
    stdout = sys.stdout
    stderr = sys.stderr

    # mock stdout to disable salt command's output
    sys.stdout = open(os.devnull, 'w')


    minions = job_info(runner, jid)
    while RETRY != 0:
        r = wait_jid(runner, jid, minions)
        if r == None:
            stderr.write('x')
            continue

        if len(r) != 0:
            stderr.write('.')
            RETRY -= 1
        else:
            break

    if RETRY == 0:
        stdout.write('max retries exceed, unreturned minions:\n    %s\n' % \
                     '\n    '.join(r))
        return

    result = job_result(runner, jid, minions)

    stderr.write('done\n')
    # restore stdout
    sys.stdout = stdout

    keys = result.keys()
    keys.sort()

    success = 0
    for k in keys:
        v = result.get(k, None)
        if v:
            s = '%d/%d' % (v[1], v[0])
            if v[1] != v[0]:
                s = highlight(s)
            else:
                success += 1
            print '%-30s: %s' % (k, s)
        else:
            print '%-30s: N/A' % k

    s = '%d/%d' % (success, len(minions))
    if success != len(minions):
        s = highlight(s)
    print '[*] Result: %s' % s

def job_info(runner, jid):
    r = runner.cmd('jobs.list_job', [jid])
    return r['Minions']

def wait_jid(runner, jid, minions):
    try:
        r = runner.cmd('jobs.active', [])
    except KeyError:
        return None

    if jid not in r:
        return []
        
    returned_minions = r[jid]['Returned']
    remains = []
    for m in minions:
        if m not in returned_minions:
            remains.append(m)
    remains.sort()
    return remains


def job_result(runner, jid, minions):
    r = runner.cmd('jobs.lookup_jid', [jid])

    result = {}
    for m in minions:
        d = r.get(m, None)
        if not d or type(d) != dict:
            result[m] = None
            continue

        success = 0
        for _, state in d.iteritems():
            rc = state['result']
            if rc:
                success += 1
        result[m] = [len(d), success]

    return result

def highlight(s):
    return '\033[31m%s\033[0m' % s

if __name__ == '__main__':
    main()
