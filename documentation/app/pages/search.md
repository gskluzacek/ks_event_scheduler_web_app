# app/pages/search.py

## Purpose
`/search`: one text box that searches accounts, players and time slots as you type.

## Results
- **Accounts** - name contains the term (shows every account when empty); admin roles also see the account id.
- **Players** - Kingshot name or id contains the term; shows the alliance name and power (admin roles also see town center level).
- **Time Slots** - only when a term is entered: the slots of players whose name matches, shown as `start - end (type)`. The end is the
  picked end (stored end + 1 second), midnight shown as `24:00`.

## Notes / Limitations
Search is not alliance-scoped yet: every role sees all accounts and players, although the requirements say results should be limited
to the viewer's alliance. Each search reads the player list and alliance names once.
