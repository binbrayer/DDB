#! /usr/bin/python
"""
MIT License

Copyright (c) 2018 Mike Binbrayer

"""
from argparse import ArgumentParser
from argparse import RawTextHelpFormatter
import os
import posixpath
import sys
import subprocess
import time
import datetime

""" Settings """
MYSQL_HOST = 'mysql'
MYSQL_USER = 'root'
MYSQL_PASSWORD = 'mypassword'
MYSQL_BACKUP_DIR = 'backups/mysql'  # path in docker container
EXCLUDE_MYSQL_DATABASES = ('information_schema', 'performance_schema', 'mysql')

MYSQL_ENV = 'docker exec ddb_mysql'
PHP_ENV = 'docker exec ddb_php'

TIMESTAMP_FORMAT = '%Y%m%d%H%M%S'  # timestamp will be added to dump files

"""
This dictionary stores fallowing settings:
key - should be used as an argument (example: 'thisScript.py database --CMS key').
doBeforeDump - what should be done before dump.
doAfterDump - what should be done after dump.
excludedTablesPatterns - what tables should be empty in the dump (cache, search, etc)

doBeforeDump and doAfterDump - lists of tuples. Each tuple contains "environment" (where command should be run) and "command" (which should be run in this environment)
"""
maintenanceCommands = \
    {
        'drupal8': {
            'doBeforeDump': [(PHP_ENV, 'drush sset CMS.maintenance_mode TRUE'),
                             (PHP_ENV, 'drush cr')],
            'doAfterDump': [(PHP_ENV, 'drush sset CMS.maintenance_mode FALSE'),
                            (PHP_ENV, 'drush cr')],
            'excludedTablesPatterns': ('cache_', 'accesslog', 'flood', 'search_', 'semaphore', 'sessions', 'watchdog'),
        },
        'testcms': {
            'doBeforeDump': [(PHP_ENV, 'php -v'), ],  # some test
            'doAfterDump': [(PHP_ENV, 'php --ini'), ],
            'excludedTablesPatterns': ('cache',),
            # if only one patter is in the list the coma (",") required after it: ('cache',) NOT ('cache')
        }
    }


""" Support """


def clear():
    """ to clear terminal """
    os.system('cls' if os.name == 'nt' else 'clear')


def whoami(n=1):
    """ returns current function name """
    return sys._getframe(n).f_code.co_name


class colors:
    reset = '\033[0m'
    bold = '\033[1m'
    underline = '\033[4m'
    red = '\033[91m'
    green = '\033[92m'
    yellow = '\033[93m'
    blue = '\033[94m'
    magenta = '\033[95m'
    cyan = '\033[96m'


""" Core """


def args():
    parser = ArgumentParser(description='''
{bold}{color}./{name} --dry{reset} - DRY run.
{bold}{color}./{name} --simulate{reset} - create dummy databases; simulate cron backups with removing old dumps; remove dummy databases;
{bold}{color}./{name}{reset} - make dumps of all database manually.
{bold}{color}./{name} myDataBase1 myDataBase2{reset} - make dump of your databases.
{bold}{color}./{name} myDrupal8Base --CMS testcms{reset} - put your site to maintenance mode before dump; make dump; up it after dump.
{bold}{color}./{name} --weekly 4{reset} - run it five+ times to make "weekly" dumps and store only four dumps.
{bold}{color}./{name} myDrupal8 --monthly 12 --CMS drupal8{reset} - good command for your Drupal schedule backups.
        '''.format(name=os.path.basename(__file__), color=colors.cyan, bold=colors.bold, reset=colors.reset), formatter_class=RawTextHelpFormatter)
    frequency = parser.add_mutually_exclusive_group()
    frequency.add_argument('--hourly', default=None, type=int, help='"--hourly 7"; hourly - frequency tag; 7 - how many dumps should be stored')
    frequency.add_argument('--daily', default=None, type=int, help='--//--')
    frequency.add_argument('--weekly', default=None, type=int, help='--//--')
    frequency.add_argument('--monthly', default=None, type=int, help='--//--')
    parser.add_argument('-d', '--dry', action='store_true', default=False, help='Dry run.')
    parser.add_argument(dest='databases', default='all', type=str, nargs='*', help='List of databases. All databases if not present.')
    parser.add_argument('--CMS', dest='CMS', choices=maintenanceCommands.keys(), default=None, help='Is used to prepare website before dump (clear cache etc).')
    parser.add_argument('--simulate', action='store_true', default=False, help='Make dummy backups and cleanup after.')
    args = parser.parse_args()
    return (args)


def exeEnv(environment, cmd, dry=False):
    """ Execute command on environment system
    if "environment" is empty - command will be executed on host system as usual,
    if "environment" is "docker exec mydockercontainer" - command will be executed in docker.
    if "dry" variable is True command will be only printed without execution

    """
    # execute = environment + ' sh -c \'' + cmd + '\''
    execute = '{} sh -c "{}"'.format(environment, cmd)
    print ('\n' + whoami(2) + '() > {cyan}{environment} sh -c "{yellow}{cmd}{cyan}"{reset}'.format(environment=environment, cmd=cmd, yellow=colors.yellow, cyan=colors.cyan, bold=colors.bold, reset=colors.reset))
    if dry:
        return 0
    else:
        try:
            response = subprocess.check_output(execute, shell=True)
        except subprocess.CalledProcessError as e:
            print (e.returncode)
            exit()
        else:
            return response


def runMySQL(cmd):
    openMySQL = "mysql -h {0} -u {1} -p'{2}' -e".format(
        MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD)
    cmd = openMySQL + " '" + cmd + "'"
    return exeEnv(MYSQL_ENV, cmd)


def genBackupPath(dataBaseName, frequency, path=MYSQL_BACKUP_DIR):
    path = posixpath.join(path, dataBaseName, frequency)
    cmd = 'mkdir -p {}'.format(path)
    exeEnv(MYSQL_ENV, cmd, args.dry)
    head, tail = os.path.split(path)
    cmd = 'chmod -R 777 {}'.format(head)
    exeEnv(MYSQL_ENV, cmd, args.dry)
    return path


def getMySQLBackupList(databases='all'):
    """ Return list of all databases if argument=='all' except EXCLUDE_MYSQL_DATABASES
    Return

    """
    if databases == 'all':
        databases = runMySQL('SHOW DATABASES;').splitlines()
        databases = databases[1:]  # Remove 'Database' frome list
        databases = list(filter(lambda x: x not in EXCLUDE_MYSQL_DATABASES, databases))
    try:
        assert (len(databases) != 0), 'No databese'
    except AssertionError as e:
        print (repr(e))
    return databases


def getMySQLIncludedTablesList(db, excludedTablesPatterns=None):
    """ Returns list of tables which should be fully dumped
    db = Database name
    CMS = one of keys from maintenanceCommands (drupal8, wordpress, testcms)
    returns list of tables name which should be dumped

    """
    allTablesNames = runMySQL('SHOW TABLES IN ' + db + ';').splitlines()
    try:  # "try" need to skip empty tables
        allTablesNames.pop(0)  # Remove title from output
    except Exception:
        pass

    if excludedTablesPatterns == None:
        return allTablesNames
    else:
        excludedTables = []
        for pattern in excludedTablesPatterns:
            for tableName in allTablesNames:
                if pattern in tableName:
                    excludedTables.append(tableName)
        includedTables = list(filter(lambda x: x not in excludedTables, allTablesNames))
        return includedTables


def dumpMySQL(db, path, CMS=None):
    filename = appendTimeStamp(db)

    if CMS:
        excludedTablesPatterns = maintenanceCommands[CMS]['excludedTablesPatterns']
    else:
        excludedTablesPatterns = None
    includedTables = ' '.join(getMySQLIncludedTablesList(db, excludedTablesPatterns))

    filepath = os.path.join(path, filename + '.sql')

    """ Dump database scheme """
    cmd = 'mysqldump --complete-insert --disable-keys --single-transaction --no-data -h {} -u {} -p"{}" {} > {}'.format(MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, db, filepath)
    exeEnv(MYSQL_ENV, cmd, args.dry)

    """ Dump only necessary tables """
    cmd = 'mysqldump --complete-insert --disable-keys --single-transaction -h {} -u {} -p"{}" {} {} >> {}'.format(MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, db, includedTables, filepath)
    exeEnv(MYSQL_ENV, cmd, args.dry)

    """ Compress """
    cmd = 'gzip -v {}'.format(filepath)
    exeEnv(MYSQL_ENV, cmd, args.dry)
    cmd = 'chmod 777 {}.gz'.format(filepath)
    exeEnv(MYSQL_ENV, cmd, args.dry)
    return 0


def appendTimeStamp(string):
    """ Returns argument with appended timestamp """
    now = datetime.datetime.now()
    now = now.strftime(TIMESTAMP_FORMAT)
    return string + '_' + now


def deleteOld(startpath=MYSQL_BACKUP_DIR, store=0, dry=False):

    def getFilesPath(startpath):
        dumpFiles = []
        tree = os.walk(startpath)
        for root, dirnames, filenames in tree:
            for filename in filenames:
                dumpFiles.append(os.path.join(root, filename))
        return dumpFiles

    dumpDir = []
    tree = os.walk(startpath)
    for root, dirnames, filenames in tree:
        if not dirnames:
            dumpDir.append(root)
    for location in dumpDir:
        dumps = getFilesPath(location)
        dumps = sorted(dumps, reverse=True)
        oldDumps = dumps[store:]  # remove N files from remove list
        if len(oldDumps) == 0:
            print ('No old dumps were found in {}'.format(location))
        else:
            if not dry:
                print ('\nFollowing dumps were removed:')
            else:
                print ('\nFollowing dumps were not removed because of dry run:')
            for oldDump in oldDumps:
                print ('\t' + oldDump)
                if not dry:
                    os.remove(oldDump)


def maintenance(CMS=None, when=None):
    """ Put website to maintenance mode and up it after dump (or do something else before and after dump)
    CMS = one of keys from maintenanceCommands
    when = doBeforeDump | doAfterDump

    """
    if not CMS or not when:
        return 0
    else:
        for cmd in maintenanceCommands[CMS][when]:
            environment = cmd[0]
            command = cmd[1]
            print (exeEnv(environment, command))


def simulate():
    """
    Generate dummy databases and execute this script Ntimes to simulate schedule backups

    """
    Ntimes = 15
    dummyDBs = ['dummyDB01', 'dummyDB02']
    settings = ['--hourly 5', '--daily 7', '--weekly 4', '--monthly 12']

    def generateDummyDumps(dbs, arguments):
        dbs = ' '.join(dbs)
        run = [sys.argv[0], dbs, arguments]
        run = ' '.join(run)
        print (run + '\n')
        print (subprocess.check_output(run, shell=True))
        time.sleep(0.1)

    """ Generate dummy databases """
    for db in dummyDBs:
        runMySQL('CREATE DATABASE IF NOT EXISTS ' + db + ';')

    for x in xrange(0, Ntimes):
        for argument in settings:
            os.system('clear')
            print ('Running {}/{} dummy dumps generation.').format(x, Ntimes)
            print ('Make dump with "{}" argument').format(argument)
            generateDummyDumps(dummyDBs, argument)

    """ Remove dummy databases """
    for db in dummyDBs:
        # pass
        runMySQL('DROP DATABASE ' + db + ';')

    print ('Finish schedule backup simulation')
    exit()


def main():
    """ Setup type of schedule and how many backups will be stored """
    if args.hourly:
        frequency = 'hourly'
        store = args.hourly
    elif args.daily:
        frequency = 'daily'
        store = args.daily
    elif args.weekly:
        frequency = 'weekly'
        store = args.weekly
    elif args.monthly:
        frequency = 'monthly'
        store = args.monthly
    else:
        frequency = 'manual'
        store = 0

    """ Make dummy databases dumps """
    if args.simulate:
        simulate()
        exit()

    """ Get list of databases for dump """
    dumpDataBasesList = getMySQLBackupList(args.databases)
    print ('Works with: ', dumpDataBasesList)

    """ Make dumps """
    for db in dumpDataBasesList:
        maintenance(args.CMS, 'doBeforeDump')
        path = genBackupPath(db, frequency)
        dumpMySQL(db, path, args.CMS)
        maintenance(args.CMS, 'doAfterDump')

    """ Remove old dumps """
    if store > 0:
        for db in dumpDataBasesList:
            dumpDir = os.path.join(MYSQL_BACKUP_DIR, db, frequency)
            deleteOld(dumpDir, store, args.dry)
    else:
        print ('\nNothing will be deleted if "--{} 0" or unset'.format(frequency))

    # ENDOFFUNCTION


args = args()
if args.dry:
    clear()
    print ('!!!DRY RUN!!!')
main()
