
# Added by piccolo

bold=`tput bold`
normal=`tput sgr0`
echo
echo "Welcome, ${bold}$FULL_NAME${normal}. Sites you have access to administer are linked in your "
echo "home folder, and public HTML files are in ${bold}~/<site_name>/public${normal}"
echo 
echo "To perform an action with a site account, use ${bold}sudo -u <site_name> <command>${normal}"
echo

umask u=rwx,g=rwx,o=
