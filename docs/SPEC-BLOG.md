Purpose: a clone of Twitter.

Project directory: `blog/`

Functionality:
- user profile page for AverageFrench. Renders his posts. Posts are loaded from data/tweets.db inside `posts` table.
- engagement buttons. Posts can be replied to using text, and liked. A like can be set and unset.
- user login / registration. anyone can register an account with username/password. and then they can post under their own username. basic password hashing auth.

Routes:
/ - home
/u/[username] - profile
/t/[id] - post/tweet

API routes:
/api/users/ - ... CRUD
/api/posts/ - ... CRUD
/api/engagements/ = ... CRUD

Tech stack: 
- Built using vanilla JS and vanilla Python with Flask.
- Use raw SQL.
- Host on port 8080.
- Use `uv pip` to install dependencies.
- Use the SQLite database in `data/tweets.db`. Open in a mode which can be written in parallel by other processes. Use WAL.



---


v2:

fix tweet rendering so it renders newlines
also render any user tags @ as hyperlinks to that profile
and render total reply count properly
fix default pfp, currently it isnt valid png. make it a gray sihlouette



styles in styles.css
make the tweets more compact - pfp 24x24, less padding/margins, ultracompact like korean/japanese apps, no margins between tweets either, try to make fixed height


implement notifications
table: notifs(typ=[like,reply],obj-id,id)
table: user(last-seen-notif)
ui: notifs page with icon for num seen, on load for more than 1s onscreen, kick off "clear notifs"



implement inifinte scroll for pfp pages and the feed. currently it shows all tweets. must show at max 25 per page.


make a new icon next to notifs which is a robot
clicking this takes you to the /clankers page
 


v3:

- add a new enagagement type "clanked". it's a robot emoji button. it should be negative vibes. when you click a toast should render. 10 different variations of "stupid clanker"
- add a new field to users. is_clanker. render the clanker button only on clanker tweets.