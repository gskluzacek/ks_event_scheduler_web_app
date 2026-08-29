# initial mock screens for NiceGUI

1. usage of time zone in `schema.py` we do not store UTC time offsets. the account table stores IANA time zone name 
   and we we collect/store naive datetime values and then assign the time zone to them and convert local time to UTC 
   time when scheduling or other time zones when displaying times to users in the web UI. (see updated time_zone table 
   info in the requirements doc)
2. account in schema.py
   1. need to discuss account_type \[discord-user | manual-user ] for users set up by admins.
   2. inquire about discord_avatar_url
   3. as discord `global_name` as `discord_global_name` in the account table
   4. think about using the IANA time zone name in the account table instead an FK???
   5. add create_account_id - set to NULL for discord-user account types or the admin's account_id for manual-user 
      account types.
   6. add update_account_id and updated_at columns
3. player in schema.py
   1. add the 4 audit columns: create_account_id, update_account_id, created_at, updated_at
4. time slot in schema.py
   1. start / end should not have date components, only time components.
   2. add time_slot_type: prefered, acceptable, and avoid 
   3. add the 4 audit columns: create_account_id, update_account_id, created_at, updated_at
   4. see updated time_slot table info in the requirements doc
5. event in schema.py
   1. events have begin and end dates, which are date only components. The do not have anything to do with the 
      schedule of the event.
   2. add columns of qty_to_schedule and active_ind
   3. add the 4 audit columns: create_account_id, update_account_id, created_at, updated_at

* \[done] give an .env.example file with the list of environment variables required.
* the text and icons in the navigagion header bar is difficult to see as there is not enough contrast between the backround and the text/icons.

Account managament
1. how do you view / edit ? it doesn't appear like there is any action that can be performed on the items in the account table.

Player management
1. I have a discord guild with my bot already added to it, can we modify one of the alliances to use this guild instead of what you have currently coded?

Time slot management
1. need mechanism to filter the displayed time slots:
   1. a player drop down that filters on which player the timeslots are displayed for.
   2. an event drop down that filters on which event the timeslots are displayed for.
   3. a (time slot) type drop down that filters on which type (prefered, acceptable, avoid) of time slots are displayed for.
   4. a validation indictor drop down that filters on indicator (True or False) of the time slots are disaplyed for.

Search
needs additional work.... but lets put that on the back burner for now.

dashboard
1. maybe have functionality where you click on a tile of the dashboard then it takes you to the respective page.
2. later I want to revisit how upcoming events are displayed on the dashboard.

user role vs admin roles
1. when an admin type role is accessing any of the maintenance pages, they are going to need to be able to apply filters to and/or search the data being displayed.
