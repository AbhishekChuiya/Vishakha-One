# Keeping Vishakha One running ("it should never go down")

Nothing can promise 100% uptime, but these four steps make the application recover on its own after a crash,
a reboot, a power cut, or a hung worker - without anyone logging in.

Run on the server (as an administrator). Service name below is `vishakha-one`; check yours with
`systemctl list-units | grep -i -E "gunicorn|vishakha"`.

1. Make the app and nginx always restart (also after reboot):

       sudo mkdir -p /etc/systemd/system/vishakha-one.service.d /etc/systemd/system/nginx.service.d
       sudo cp vishakha-one.service.d-override.conf /etc/systemd/system/vishakha-one.service.d/keep-running.conf
       sudo cp nginx.service.d-override.conf /etc/systemd/system/nginx.service.d/keep-running.conf
       sudo systemctl daemon-reload
       sudo systemctl enable vishakha-one nginx postgresql

2. Install the watchdog (checks `/healthz/` every minute; restarts the app after 3 failed checks):

       sudo install -m 755 vone-watchdog.sh /usr/local/bin/vone-watchdog.sh
       sudo cp vone-watchdog.service vone-watchdog.timer /etc/systemd/system/
       sudo systemctl daemon-reload
       sudo systemctl enable --now vone-watchdog.timer

3. Test it (you should see `{"status":"ok"}`):

       curl -s http://127.0.0.1:8101/healthz/

4. Try a crash on purpose during a quiet moment and watch it come back within a minute or two:

       sudo systemctl kill -s SIGKILL vishakha-one ; sleep 10 ; systemctl is-active vishakha-one

See what the watchdog did: `journalctl -t vone-watchdog --since today`.

Also worth doing (ask IT): put the server on a UPS, enable automatic start after power loss in the BIOS,
and monitor `https://<your address>/healthz/` from another machine so someone is alerted if it fails.
