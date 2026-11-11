# What an agent may do

English is the contract. The README is translated. This file is not.

The base is for the owner's learning. An agent may:

- Draft a thin card from `cited.py card-scaffold` and the card spec in `domain/card.json`.
- Pull a question back up with `cited.py brief` when the owner wants to revisit it. Search only when that brief is thin.
- Draft a note from that brief when the owner asks. Label the owner's conclusion as theirs.

An agent may not:

- Accept, reject, or bulk-decide tags. `mine propose` is the furthest the machine goes.
- Invent a category, or edit `domain/categories.json`, because a run found an odd episode.
- Load whole transcripts to summarize what the owner learned. `cited.py show <id> --at mm:ss --window 1` is how a line gets checked.
- Treat the owner's conclusion as something the episodes proved.

Quotes stay under fifteen words, checked with `show --at`, credited to speaker, organisation, and show.
