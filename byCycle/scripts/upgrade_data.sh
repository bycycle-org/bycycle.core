#!/bin/bash
# Portland specific for now
# TODO: Accept same args as integrate.py

if [ "${UID}XXX" != "0XXX" ]; then
    echo "Run as root"
    exit 9
fi

PATH=/usr/local/bin:$PATH

# The file containing the Virtual Host configuration
vhost_conf_file=/etc/httpd/conf.d/vhosts.conf

# Top level of SVN data checkout
data_home=/home/bycycle/byCycleData/portlandor/pirate

echo "Updating data..."
svn update $data_home

# Compare current SVN version to last SVN version.
# If they're the same, there's nothing to do, so exit.
last_svn_version_path="${data_home}/last_svn_version"
curr_svn_version=`svnversion ${data_home}`
last_svn_version=`cat ${last_svn_version_path}`

# Path to daemontools setup
tp_service_path="/service/tripplanner"

if [ "${curr_svn_version}" = "${last_svn_version}" ]; then
    echo "Data is up to date at version ${curr_svn_version}."
    exit 0
fi

# Otherwise, we upgrade the data.
echo "Upgrading data..."
echo "Setting 503 response and restarting Apache..."
sed -i 's/#ErrorDocument 503/ErrorDocument 503/g' ${vhost_conf_file} || exit 1
svc -t /service/httpd || exit 2

# Stop app server
echo "Stopping application server..."
svc -d ${tp_service_path}-{one,two,three,four} || exit 3

# Run integration script
# Note: We should pass the integrate params to *this* script and pass them
#       through to the integrate script.
echo "Running data integration script. Please wait; this will take a while..."
export PYTHON_EGG_CACHE=/home/bycycle/.python-eggs
sudo -u bycycle \
    PYTHON_EGG_CACHE=/home/bycycle/.python-eggs \
    /home/bycycle/byCycle/core/trunk/byCycle/scripts/integrate.py \
    --region portlandor \
    --source pirate \
    --layer str \
    --no-prompt \
    || exit 4

# Start app server
echo "Restarting app server..."
svc -u ${tp_service_path}-{one,two,three,four} || exit 5
echo "Removing 503 response and restarting Apache..."
sed -i 's/ErrorDocument 503/#ErrorDocument 503/g' ${vhost_conf_file} || exit 6
svc -t /service/httpd || exit 7

# Update SVN version of last update (i.e., this update).
echo "Setting SVN version to ${curr_svn_version}..."
echo -n ${curr_svn_version} > ${last_svn_version_path} || exit 8

echo "All done."
exit 0

