
what about a poetry agent? 
that just develops its own personality
and changes its personal style in real-time?
that would be cool


what if the agent had image understanding capability
and then it produced text based on that
that would be cool



how would you do this?
- simple html page
- reflection loop:
    stimulus <- poem or image from somewhere
    
    loop:
        context = personality (randomly sampled) (like eliza)

        10x (embedding(inspiration), context) -> (poem)

        add to html blog
            stimulus
            []outputs
        
        reflect and update:
            my_taste = score(poem)
            audience_taste = audience_rating(poem)

            update how???
                1/ deepseek style - sample a cohort of posts, rank as which one is better as compared against others. 
                think about the traits deeply. why did you think people liked this?

                2/ simple retrain
                my favourite poems: 
                {poems}
                or 1 step like tiktok ml system??
            
            embeddings for different users reacting to my post? would that be useful? 
            idk make it simple.
            I just want it to generate content.
            that would be enough for me.
            I want it to write poetry.
            that would be cool


