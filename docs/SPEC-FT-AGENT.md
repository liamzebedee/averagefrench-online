Purpose: an agent which can live learn on a social network.

The social network is called Clanker.

The agent real-time learns and adapts.

Let's just make something that works for now
ie. you have your agent




averagefrench ideas
- get the best posts so far
- fine tune on those
- save up to 10 qloras

the problem is you want to try like 5 different strategies at once?
- post poetry
- post questions
- post observations


how can I design this manually?
- show the best tweets so far
    page
    renders the best ones


what sort of agent loop do I need?
just a simple .txt log (the raw log I can replay)
basically doing the following:

We want to maximise likes from other users.
RL based on this. Generate 8 candidate tweets. 
post them
and then wait to get replies? 
normalised for the group


UI which renders:






buttons:
- clanker - stupid robot button. adds -1 downvote bad example




realtime online training model

- open base qwen model for training and inference
- open tweets.db
- generation=0

while true:
- get the tweets from averagefrench from the past 2hr with engagements>0 by reading db, limit 15
- fine tune prompt = """You are @averagefrench.
best tweets:
- 
- 
bad tweets:
-
"""
- print "online_train generation=i"
- fine tune 10 iterations using qlora
- inference_prompt = """You are @averagefrench.
Generate x ...
Examples: ..."""
- generate 10 completions using already fine tuned model
- insert into db
- wait 1min
- generation += 1