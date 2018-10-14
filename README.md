# DDB - Docker Databases Backup Tool
This project is not about web servers, databases or Docker. This project is about how to backup databases out of Docker container and organize its schedule. **Do not use it on production "as is" - configure it before.** 
This backup script is designed to work with MySQL database but you can easily add another database (or ask me to do that).

This project contains an example of Docker LNMP stack with addition **cron** container based on **docker:stable** (backup script will be run inside it). Core of this project is **backup.py** script.

## Core Functions of <u>backup.py</u>
* Can be used **inside** and **outside** Docker.
* **Cron** friendly.
* All settings are set up as arguments.
* Has **maintenance** functionality (can put web-site to maintenance mode or do other staff before dump).
* Can dump **all databases** or specified database.
* Has option to **dry run**.
* Has **simulate** option (creates dummy databases; simulates schedule backup; drops dummy databases).
* Designed to only map tables like *cache* or *search* (to avoid unnecessary data in dumps).
* Easily **extensible** to other systems.

## Required
* [Docker](https://docs.docker.com/install/ "Install Docker")
* [Docker Compose](https://docs.docker.com/compose/install/#install-compose "Install Docker Compose")
* Be able to [manage Docker as non-root user](https://docs.docker.com/install/linux/linux-postinstall/#manage-docker-as-a-non-root-user "Manage Docker as a non-root user")

## Quick Start
1. Run **`init.sh`** to create project directories structure.
2. Run **`docker-compose up`**.
> Docker container named **cron** will run backup script by cron inside itself with predefined parameters (look in **crontab** file) and each minute will make *weekly* backup of *myDataBase* (example empty database). You'll find dumps of that database in **backups/mysql/myDataBase/weekly** (will be stored last 4 dumps).
3. Run **`backup.py`** manually.
> In this case script will be run inside your host system not inside Docker. Without any arguments it will make dumps of all available databases (except service databases). Old dumps will not be deleted. You'll find dumps in **backups/mysql/myDataBase/manual** (because only one example database is present).
4. Run **`backup.py -h`** to see help with examples.

## Available Parameters
**!!! this section may not be relevant. run `backup.py -h` to obtain relevant information !!!**
```
positional arguments:
  databases             List of databases. All databases if not present.

optional arguments:
  -h, --help            show this help message and exit
  --hourly HOURLY       "--hourly 7"; hourly - frequency tag; 7 - how many dumps should be stored.
  --daily DAILY         --//--
  --weekly WEEKLY       --//--
  --monthly MONTHLY     --//--
  -d, --dry             Dry run.
  --CMS {testcms,drupal8} Used to prepare website to dump (put site to maintenance mode, clear cache, etc).
  --simulate            Make dummy backups and cleanup after.

```
## Example Usage
* **`./backup.py`** - make dumps of all database manually.
* **`./backup.py --dry`** - DRY run.
* **`./backup.py --simulate`** - create dummy databases; simulate cron backups with delete old dumps; remove dummy databases;
* **`./backup.py myDataBase1 myDataBase2`** - make dump of your databases.
* **`./backup.py myCMSDataBase --CMS testcms`** - put your site to maintenance mode before dump; make dump; up it after dump.
* **`./backup.py --weekly 4`** - make "weekly" dumps and store only four dumps (try to run it five+ times).
* **`./backup.py myDrupal8 --monthly 12 --CMS drupal8`** - good command for your Drupal8 schedule backups.

## Schedule Backups
You have two options to organize schedule backups:

* Run backup script by host system cron (you should comment cron section in **docker-compose** file).
* Edit **crontab** file according to your requirements (in this case cron job will be run inside Docker).

## Some Notes
Run **`docker container ls`** after start. If containers ***ddb_mysql*** and ***ddb_php*** are absent (are present as ***backuptools_mysql*** and ***backuptools_php***) - edit ***MYSQL_ENV*** and ***PHP_ENV*** according to proper names in your system.

---

On production server do not forget about [restart policy](https://docs.docker.com/compose/compose-file/#restart, "Docker restart policy").

---

You can use backup script without Dockers. Just set ***MYSQL_ENV*** and ***PHP_ENV*** to blank and all commands will be run on the host system.

## Fin
Fill free to ask me any question and request new features.
