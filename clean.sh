BASEDIR=$(dirname "$0")
sudo rm -r $BASEDIR/backups
sudo rm -r $BASEDIR/var

mkdir -p $BASEDIR/backups/mysql
mkdir -p $BASEDIR/var/lib/mysql
mkdir -p $BASEDIR/var/log
