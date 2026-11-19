# Bring the old Vishakha One content (documents, news, videos, menu ...) into the new version

You do NOT need to upload anything again by hand. Content lives in two places in any copy of the application:
the database (`db.sqlite3`) and the `media` folder (the uploaded PDFs, images, videos). Move both together.

## A. On your PC (local) - from the OLD project folder

In PowerShell, inside the NEW project folder (venv active). Change the two paths to where your OLD project is
(the folder that contains the old `db.sqlite3` and `media`):

    mkdir D:\temp
    copy "D:\Projects\VishakhaOne_old\db.sqlite3" D:\temp\old_copy.sqlite3

    $env:VONE_SQLITE_PATH = "D:\temp\old_copy.sqlite3"
    $env:VONE_MEDIA_ROOT  = "D:\Projects\VishakhaOne_old\media"

    python manage.py migrate
    python manage.py export_content D:\temp\old_content.zip

    Remove-Item Env:VONE_SQLITE_PATH
    Remove-Item Env:VONE_MEDIA_ROOT

`migrate` here upgrades only the COPY (`old_copy.sqlite3`), your old files are untouched.
`export_content` prints how many items it found and lists any uploaded file it could not find on disk.

Then bring it into the new project:

    python manage.py import_content D:\temp\old_content.zip --dry-run
    python manage.py import_content D:\temp\old_content.zip

`--dry-run` shows what would happen and changes nothing. Running the import twice is safe (it updates, it does not duplicate).

## B. On the SERVER

The server already has its own database and media folder, so after you deploy the new code and run `migrate`
everything that is on the server is still there. Nothing to import on the server.
If you want the server's content on your PC for testing, run on the server (inside `/srv/vishakha-one/app`, venv active,
same environment variables the service uses):

    python manage.py export_content /tmp/vone_content.zip

copy the zip to your PC with `scp`, then run the two `import_content` commands from section A.

## What is and is not copied
Copied: applications, helpful links, news / announcements / circulars, policies and documents, videos, brochures,
jobs, new joiners, events, canteen menu, thoughts of the day, and every uploaded file they use.
Not copied (on purpose): employee accounts and passwords, notifications, audit history, bookmarks, push subscriptions.
Imported notices never trigger push notifications.
