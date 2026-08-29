# Document Purpose

This document contains the requirements for the Kingshot Event Scheduling Web Application. The application is designed
to facilitate the managment of player's available time slots and the scheduling of Kingshot events at optimal times.

# Technical Stack

the application will be build using the following technologies:

1. Python 3.14 or later
2. NiceGui for build the web application user interface
3. HTTPX for making HTTP requests.
4. FastAPI for implemnting additonal functionality / flows.
5. Python-Dotenv for managing environment variables and configuration settings.
6. SQLite intially for the Database, with the option to migrate to PostgreSQL possibly in a Docker Container.
7. Redis (in a Docker Container) if the needs of caching exceeds the capabilities of NiceGui's built-in caching.

# Application Functional Overview

The application can be divided into the following functional areas:

## Account Management:

1. All users - This area will handle user account registration, and profile management. Users will be able
   to create an account, view and edit their personal information, set their prefered local time zone and 
   any other account preferences.
2. Users with the Admin role - will be able to manage the all accounts within their Alliance. This includes 
   creating, editing, and deleting users' accounts. With perhaps the exception of private or sensitive information.
3. Users with the PowerAdmin role - have the same abilities as Admins and will also be able to assign and manage 
   roles for all users within their Alliance.

## Player Management

1. All users - This area will allow users to add their Kingshot players with their corresponding Kingshot 
   Kingdom, Alliance and other attributes. Users will be able to view, edit and delete their players as needed.
2. Users with the Admin or the PowerAdmin role - will be able to manage the players within their Alliance. This 
   includes creating, editing, and deleting users' players.

## Time Slot Management

1. All users - This area will allow users to manage their available time slots for Kingshot events. Users will be 
   able to add, edit, and delete the time slots for their players.
2. Users with the SchedulerAdmin or the PowerAdmin role - will be able to manage the time slots for all players 
   within their Alliance. This includes creating, editing, and deleting time slots for any player.

## Event Management

1. All users will be able to view the list of Kingshot events and their details, including the event name, 
   scheduled times and dates, if appliable.
2. Users with the SchedulerAdmin role or the PowerAdmin role will be able
   1. to create, edit, and delete Kingshot events.
   2. to run the scheduling algorithm that determine the optimal time for each event based on the available time 
      slots of all players.
   3. to edit the even schedule, as needed, to ensure that the maximum number of players can attend each event 
   4. to publish the final schedule for all users to view
   5. mark player time slots as needing review by the player to confirm if the time slot is still valid for them 
      for the given event.

## Search

1. by using search forms, users will be able to see who from their Alliance has registered Accounts, the 
   players that have been added, and the time slots that have been created for each player. This will allow users 
   to see which players are available at specific times and dates, and help them plan their Kingshot events 
   accordingly.  
2. All users will be able to run search forms to search, view, filter & sort the following details for their Alliance:
      1. accounts registered within their Alliance
      2. players belonging to each account
      3. time slots created for each/all players
3. Users with elevated roles (Admin, PowerAdmin, SchedulerAdmin) may be able to view additional attributes for 
   each of the above items.

## Site Maintenance

1. Users with the SuperAdmin role will be able to manage the overall application, including managing user accounts, players, time slots, and events across all Alliances.
2. This includes the ability to create, edit, and delete user accounts, players, time slots, and events for any Alliance.
3. Additionally SuperAdmins will have the ability to manage system-wide settings and data, such as:
   1. Managing the list of Kingdoms and Alliances and their associated Discord guilds
   2. Managing the list of IANA time zones and their associated UTC offsets


# Data Model Overview

## tables

* kingdom
* alliance
* account
* player
* time_slot
  * columns: time_slot_id, player_id, event_id, local_start_time, local_end_time, time_slot_type, priority, 
    validated_indicator
  * we store only start time and end time, no date components.
  * time slot types are: prefered, acceptable, and avoid.
* event
  * columns: event_id, event_name, event_desc, qty_to_schedule, begin_date, end_date, active_ind, create_account_id, 
    create_date_time, update_account_id, update_date_time
  * 
* role
* player_role - is this needed?
* time_zone
  * columns: time_zone_id, region, location. 
  * the IANA time zone name is split into region and location to facilitate selecting a complete IANA time zone name from two drop down lists. 
  * The user first select the region drop down (select distinct region from time_zone), 
  * then the location drop down is populated with just the locations within the selected region (select locaiton from time_zone where region = selected_region). 
  * The complete IANA time zone name is then constructed by concatenating the region and location with a forward slash (/) in between.
  * internally we use the python dateutil package `local_tz = tz.gettx(users_iana_time_zone_name)` to get the user's corresponding tzinfo object.
  * we collect/store naive datetime values and then assing the time zone to the naive datetime values with `local_dt = naive_dt.replace(tzinfo=local_tz)`
  * finally we convert the local datetime to UTC with `utc_dt = local_dt.astimezone(timezone.utc)`

## relationships

* kingdoms have one or more alliances
* an alliance belongs to exactly one kingdom
* an alliance has one discord guild
* a discord guild belongs to exactly one alliance

* time zones define IANA time zones and are used to convert between UTC and local time for each account
* multiple accounts can have the same time zone
* an account has exactly one time zone

* a person registers an account
* an account can add one or more players
* players are assigned a role (User, Admin, PowerAdmin, SchedulerAdmin)
* each player belongs to exactly one Alliance (and by relation to that allince's Kingdom)
* each player can have one or more time slots for a given Kingshot event
* a time slot defines a specific time in the players local time zone, when the player is available to participate in a Kingshot event
* each time slot is associated with a specific event and player
* events belongs to exactly one Alliance
* a player can only create time slots for events that are associated with their Alliance

notes:
* since the SuperAdmin role is a system-wide role, it is not associated with any specific Alliance. As such, it 
  cannot be assigned at the player level, but rather at the account level. so the player_role table cannot be for the
  SuperAdmin role and a different mechanism will be used to manage the SuperAdmin role at the account level.

# Integrations

The primary integration for the application will be with Discord. 
* It will be used for account registration, authentication and possibly for role management within the application
* Additionally it will be used to verify memershipt to the Alliance's Discord guild before allowing users to and a 
  player to an Alliance.
* we may also use Discord to send notifications to users or publish messages to the Alliance's Discord guild.

## Account Registration flow

1. User visits the web app's home page and clicks Register Account navigation item to begin the registration process.
2. The register account page & displays login with discord button (contains a `state` parameter to prevent CSRF attacks).
3. The user clicks the login with discord button
4. If the user is not currently logged into Discord on the web, they will be redirected to the Discord login page, 
   where the user must successfully log in to their Discord account.
5. The user will be redirected to the Discord authorization page, where they will be promted to authorize the web 
   application to access their Discord account information by clicking the Authorize button.
6. When the user clicks the Authorize button, they will be redirected back to the web application with a 
   specifically formed URL that contains the `state` value previously sent as well as an one time use authorization 
   `code`.
7. Where a FastAPI route will:
   1. Validate the `state` value to ensure it matches the one previously sent to Discord.
   2. Exchange the authorization `code` return by Discord for an `access token`
   3. Use the `access token` to make an API request to Discord to retrieve the user's Discord account information
8. Upon successful retrieval of the user's Discord account information, we prompt the user to select their local 
   time zone from a list of IANA time zones and to provide any other required information to complete their account 
   registration.
9. The user selects time zone, etc. and then submits the registration form.
10. A record is inserted into the account table containing all required information.

## Player Joining Alliance flow

Notes/Thoughts:
* should we require the discord member to have a specific role in the Alliance's Discord guild before allowing 
  them to add a player to the Alliance?
* for accounts with multiple players under different alliacnes, might the requirement that the player be a member 
  of mutliple discord guilds be too burdensome?
* what about a player that moves between alliances on a regular basis? How should we handle that?

1. after completing the account registration process, the user clicks the Player Management navigation item and 
   then clicks the Add Player button.
2. We prompt the user to select a Kingdom, then an Alliance within that Kingdom. This determines the Discord guild 
   that will be used to verify the user's membership in the Alliance's Discord guild.
3. The Discord Guild that corresponds to the selected kingdom and alliance is displayed along with a Verify Guild
   Membership button
4. The user clicks the button and the the web app
   1. verify guild membership server-side with the BOT token
   2. we get confirmation that the discord user belongs to the discord Guild - 200 \[OK]
   3. if we get we get a 404 \[NOT FOUND] – the user does not belong to the discord guild and we display an error 
      message.
   4. we could also get a 403 \[FORBIDDEN] which would indicate that something wrong with the Bot credentials or 
      a 500 \[INTERNAL SERVER ERROR] which would indicate that something went wrong with the request, maybe the 
      bot was removed from the guild.
5. if the user is a member of the guild, we get the discord user’s member object containing user’s guild 
   nick (discord_nick_name on the specified guild)
6. We the prompt the user for the following information from the Kingshot game:
   1. Their Kingshot id
   2. Kingshot name
   3. Power
   4. Town Center level – selected from a drop down
   5. Other details as seen fit
7. A record is inserted into the player table containing all the required information.

