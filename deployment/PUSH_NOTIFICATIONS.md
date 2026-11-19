# Browser push notifications - how it works and what to do

## What employees experience
1. After signing in, a small card asks "Get notified on this device?" (shown 2-3 seconds after the page loads).
   - **Turn on**  -> the browser shows its own "Allow notifications?" box -> Allow.
   - **Not now**  -> we do not ask again for 7 days. They can also switch it on later in My profile > Notifications.
2. From then on a pop-up appears on that device (even when the tab is closed) for:
   - **Approval requested** - to approvers, when someone submits content for approval
   - **Content approved** / **Changes requested** - to the person who submitted it
   - **Company news, Leadership messages, Circulars** - to everyone, when published
   - **Announcements marked Important or Urgent** - to everyone, when published
   Tapping the pop-up opens the right page. Each item notifies once (editing it later does not notify again).
3. Signing out stops that browser receiving that person's notifications.

## One-time setup (administrator)
1. Install the new libraries (once): `pip install -r requirements.txt`
2. Make the keys (once):  `python manage.py generate_vapid_keys`
   Put the three lines it prints into the environment file used by the service (e.g. `/etc/vishakha-one/staging.env`):
       VONE_VAPID_PUBLIC_KEY=...
       VONE_VAPID_PRIVATE_KEY=...        <- secret: never share or commit
       VONE_VAPID_SUBJECT=mailto:it-support@vishakha.com
   Restart the application. Without these keys push stays quietly switched off.
3. For notices scheduled for a future time, run this every 5 minutes from cron:
       python manage.py send_due_notice_pushes
4. Optional daily tidy-up: `python manage.py archive_expired_content`

## Requirements the browser enforces (important)
- The site must be opened over **HTTPS with a certificate the browser trusts** (or on `localhost` for testing).
  A self-signed certificate (typical for an address like https://27.109.18.116:8443) will NOT work: browsers refuse
  push for untrusted certificates. Use a proper hostname with a real certificate (for example the planned
  one.vishakha.live) before rolling push out.
- The server must be able to reach the push services of the browsers over HTTPS:
  fcm.googleapis.com (Chrome/Edge/Android), updates.push.services.mozilla.com (Firefox),
  *.push.apple.com (Safari / iPhone), *.notify.windows.com. Ask IT to allow these outbound.
- iPhone/iPad: works only after "Add to Home Screen" (iOS 16.4 or newer).
- If a person blocked notifications in the browser, only they can unblock it (padlock icon in the address bar).

## Testing
1. Sign in, turn notifications on (My profile > Notifications).
2. In Content Manager, publish a Circular. A pop-up should arrive within seconds.
3. Submit something for approval from one account; the approver's browser gets "Approval requested".
