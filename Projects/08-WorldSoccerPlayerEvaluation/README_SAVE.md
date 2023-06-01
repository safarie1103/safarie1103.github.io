<a name="br1"></a>InternationalSoccer PlayerRatings

DSC 530 FINAL PROJECT

EDRIS SAFARI




<a name="br2"></a>Fédération Internationale de Football Association(FIFA ) publishes*Player rating data set which contains over 85 features about 18000players. The feaures and players are updated annually and playersare rated from 1(worst) to 100(best) . The data set can be used forvarious purposes, one of which is in the gaming industry.*

*The goal of this study is to explore the 2019 publication of thisdataset using statistical and programatic techniques.*




<a name="br3"></a>Dataset description

• Single csv file

• 18209 observations

• 89 features

• 34 features recording each player’s skills with rating of 1(bad) to 100(good)

• ‘Potential’, ‘Overall’ features show the ratings based on various features such as

skills, age, etc.. Their value ranges from 1(bad) to 5(good)

• Other features of interest:

• Age, weight, height



<a name="br4"></a>Data Preparation

• Import Dataset

• Replace ‘lbs’ from the weight and convert to integer

• Convert height from “ft’inch” to Inches as type integer place in new

column(Height\_Inch)

• Compute experience in years from signing date



<a name="br5"></a>Question

• Is the overall rating of players govern by their skill set.



<a name="br6"></a>Data Exploration-Best in skill

` `Best player in each skill category. LionelMessi is the best overall player and is bestrated in more skills than others.



<a name="br7"></a>Data Exploration- Distributions



<a name="br8"></a>Data Exploration- Distributions




<a name="br9"></a>Data Exploration- Distributioncomparison




<a name="br10"></a>Data Exploration- Distribution



<a name="br11"></a>Data Exploration- Distribution



<a name="br12"></a>Data Exploration- Distribution



<a name="br13"></a>Data Exploration- Distribution



<a name="br14"></a>Data Exploration- Scatter plot



<a name="br15"></a>Modeling Coefficients



<a name="br16"></a>Modeling Correlations



<a name="br17"></a>Modeling



<a name="br18"></a>Modeling – All Skills



<a name="br19"></a>Modeling – Less Skills




<a name="br20"></a>Summary

` `The focus of this analysis was to determine which of the attributes in the dataset contribute themost to players rating. We focused on the 34 skills and found that even though there werecollinearity among them, they are a good predictors of the overall rating.

` `We analyzed distributions, correlations, and ran the data through ordinary least square model andcharted the result. When all skills were included the model fit better.

` `Further evaluation of data and other attributes would reveal more insight to not just overall rating,but also player selection, positioning and other aspects of the game.

` `It would be interesting to see if height can be a predictor of heading accuracy, or weight with speedand/or stamina.

` `The main challenge of this study was lack of experience interpreting statistical findings. With moreexperience and using tools available, I believe I can overcome this challenge.




<a name="br21"></a> The skills rating had multicollinearity. We caneliminate them using a backward eliminationtechnique by evaluating the coefficients, R2 and p-value at each iteration.

|Conclusions||<p>The prediction model was run with all skills and a</p><p>subset. The prediction suffered when some skills were</p>|
| :- | :- | :- |
removed.

You need all the skills you can

get to be number one.

The dataset and its analysis can answer many other

questions related to whether a player should besigned, what rate should the compensated, how longa contract to offer, can be a starter or better be on thebench until certain point in the game.
