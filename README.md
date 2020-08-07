# zakanda, a technical overview

> **Note**: This is the public version of the private zakanda repository (which contains the entire commit history)

## Introduction 
[zakanda](https://www.zakanda.com/) is my first entrepreneurial endeavor which... failed miserably. You can read the juicy details in 
[my epic fail as a sports betting entrepreneur](https://dimyg.github.io/posts/my-epic-fail-as-a-sports-betting-entrepreneur/) story. 

It was aspired to be a sports betting community where anyone could bet with virtual money, track their performance, 
compete with their friends, follow others players. The betting experts which would stand out, would be able to create 
premium services to which others could subscribe to, paying them for their valuable advices. 
The main income stream for zakanda would come from commissions from these payments. 

![Landing page](https://github.com/dimyG/zakanda_public/blob/master/static/img/readme/zakanda_landing_page.png)

It is important to understand that zakanda is not a bookmaker. You can't bet with real money. A typical use case, if you are a betting expert 
and people want your advices, 
would be something like this: You spot a great betting opportunity. You bet on it in your bookmaker account. You then repeat the same 
bet in your zakanda account (with virtual money). Your zakanda followers receive an email and a notification about your latest bet. 
If your account is premium, only the followers that are subscribed to your paid service are notified. 
The wider term that describes services similar to zakanda is _tipping services_. 

## Main features
### Virtual money
(No, this has nothing to do with blockchain, digital currencies or ICOs...)  
Let's begin with a standard convention of tipping services which is to use 
units instead of virtual money. This means that instead of betting a 
specific amount, you bet in units. Usually each bet can be between 1 and 5 units. 1 for small bets and 5 for the big ones. 
Zakanda is a bit different. It tries to completely mirror your bookmaker account. If you have a balance of 2000 euros in your bookmaker 
account then you would have 2000 virtual euros in your zakanda account too. If you made a bet of 50 euros, you would copy 
that bet in zakanda using 50 virtual euros. This means that you have a very clear overview of your overall performance through 
the years.

### Bet Groups
The main organization unit in zakanda is the Bet Group. Each bet group has its own balance, bets and settings. 
Every deposit and every bet that you make, must be assigned to a specific bet group. 
When a user is registered, a bet group is automatically created for him and everything he does happens within this 
default bet group. His deposits and bets are assigned to it by default. He doesn't need to know about the concept of bet groups in order to use zakanda. 
 A user can create as many bet groups as he likes. Doing it, 
his total balance would be the sum of the balances of each individual group. When he makes a bet he can 
assign it to the bet group of his choice. A typical use case would be to create one bet group for each of your betting 
strategies and monitor the performance of each strategy individually. Your followers could choose for which bet groups 
they will be notified and by what means.  

![Bet group types](https://github.com/dimyG/zakanda_public/blob/master/static/img/readme/bet_group_types4.png) 

### Private bets and Premium services
A bet group can be of one of three types: _Free_, _Private_ or _Premium_. When you bet using a free bet group, then all your 
followers would be notified for your bet while your open bets (bets that don't have a result yet) would be 
visible by everyone. This is the default type for a bet group. 
A private bet group is one for which your followers will not be notified for the bets assigned to it and also they will not be 
able to see your private open bets. The third available type is the premium one. In order to be able to create a premium 
bet group you must first become a seller, which means that you need to provide some additional information about you. Once you 
do this, you will be able to attach a paid service to your premium bet group, choosing how much you want to charge for a 
monthly subscription. You can modify the type of a bet group whenever you want.  

![Private bets](https://github.com/dimyG/zakanda_public/blob/master/static/img/readme/private_example2.png) 

### Performance dashboard
Every user has a dashboard which contains a lot of valuable information about his overall performance like ROI and yield. 
What makes the zakanda dashboard unique though, is the fact that the charts are interactive. Each chart is automatically filtered 
by your active selection on another chart. Using this interactivity 
you can very easily isolate the bets of interest and explore various data that describe the filtered bets. This behaviour 
would become clear if you play with the charts yourself. 
For example using the Bets Status pie select the _won_ bets and then from them, select the ones made in the _double chance_ market using the Market pie. 
All other charts have been automatically filtered to describe this specific group of selected bets. This means that 
you can extract a lot of valuable information about them, like their average return. 

![Dashboard](https://github.com/dimyG/zakanda_public/blob/master/static/img/readme/dashboard3.gif) 

### Hidden amounts
As we already said, zakanda tries to mirror a user's bookmaker account with the use of virtual money. This feature is 
excellent for long term performance tracking but imposes another challenge: Privacy. Having the 
bet balance visible by everyone might make some users feel a bit uncomfortably. This is not a small issue and to 
tackle it zakanda offers you the possibility to hide your balance and bet amounts, while still being able to 
mirror your real balance and share your betting tips with your followers and subscribers. It achieves this by automatically converting your bet amount to 
percentage of your balance for each bet and converting your real bet balance to units, where one unit represents your 
average bet amount. To make it clear: Other users 
will see your balance as units and your bet amounts as percentages of that balance, but you and you alone, will see them 
as the absolute values that they really are. This way all parties get what they want. You also have the possibility to see your 
account the way others see it (with units and percentages) simply with the press of a button.  
 
![Hidden amounts](https://github.com/dimyG/zakanda_public/blob/master/static/img/readme/cash_on_off_3_forever.gif)

## System design and deployment
### System design
zakanda is composed of at least three different processes: A _web_ process, a _worker_ process and a _scheduler_ process. 
The web process is responsible for handling the http request - response cycle. It receives the client's request and 
generates the response. 

Any long running tasks like sending notification emails 
to followers, are off loaded to a queueing system to be executed as background jobs. The task is added to a queue and is processed by the first available 
worker process. You can have as many worker processes as you like. The same though is not possible for the web process. 
The web process hasn't been created with concurrency in mind, so, to be able to have more than one web processes running at the 
same time, some changes might be necessary. These changes should tackle any possible race conditions that arise from 
the current version of the code. 

The scheduler process which must always be up and running, checks periodically a specific queue for any 
task that has been scheduled for execution at a specific point in time. If it is the time for a task, the scheduler 
puts this task in the workers queue to be executed by the available worker processes. Examples of scheduled periodic tasks 
are calls to the data source API for specific data: Getting the sports schedule of the next days, the bookmaker odds 
for sport events, the results of the latest events etc.     

### Deployment
zakanda was initially deployed in Heroku where each process was a dyno. Later though it was containerized and deployed to AWS Elastic Container Service (ECS). 
In the containerized version the web "process" which in the context of ECS is called web task, is composed of two containers: 
a gunicorn service (with synchronous workers) which runs behind an nginx service that acts as a buffering reverse proxy. 
There are a lot of good reasons for such a configuration but they are out this post's scope. The worker and scheduler tasks 
contain the worker and scheduler containers respectively. Currently there is no automated deployment pipeline in place, but if 
zakanda was to become open to users again, such an automated pipeline would be more than necessary.  

## Tech stack
### Introduction
As a web application, zakanda has of course both a client and a server part. The server part, the back end of the application, 
is written in django. The front end is a typical web client composed of html rendered in the server using django templates, css and javascript. 
Notice though the catch:
Despite the fact that the server responds with rendered html, zakanda is a single page application... Sorry, what? 
As a complete beginner as I was when I started zakanda, I made an immature 
decision which cost me a lot of time down the line. 
I chose to make zakanda a single page application without using a proper front end framework like React, Angular or Vue. 
I just did it using [pjax.js](https://github.com/defunkt/jquery-pjax), 
AMD modules and [require.js](https://requirejs.org/). This is not how single page applications are made nowadays, so 
some additional information regarding the front end part of the codebase might be necessary. 

### The front end
So, pjax.js is a jQuery plugin that uses ajax and pushState to deliver a fast browsing experience by asynchronously updating 
a web page without the need to fully load the entire page from the server. 
All links are pjax enabled links, which means that they use ajax to communicate with the server. When a link is pressed 
pjax will send an ajax request to the server and will update the url using the history API. The server will respond with 
a rendered html that will replace a specific portion of the page. 

In high level, this is how a zakanda web page is updated:
1. User navigation is performed, for example a pjax link is pressed or a back/forward operation is invoked.
2. The url changes and an ajax call is made to the server
3. The server responds with rendered html.
4. A portion of the page is updated with the new html. 
5. The pjax:end event is caught by an event listener. 
6. The event listener triggers code that matches the url using regular expressions. 
7. Specific actions are executed based on the matched url.

Every javascript file is an AMD module which might require other modules to be loaded first, in order to use things 
from them. It can also export code for other modules to use. It is important to note that no zakanda variable 
pollutes the window's global namespace. Any variable that needs to be shared, is exported from its module and required 
by the module that needs it.

Writing a single page application at the scale of zakanda without using a proper front end framework is not an easy task. 
You have to pretty much reinvent the wheel in some occasions. For example you have to write 
a proper front end routing functionality, listening to the proper browser and pjax events and triggering the required actions. 
You must also keep track of user interface changes and propagate them to the rest of the application 
simply using jquery. These things make the whole front end codebase prone to bugs and difficult to maintain. Front end 
frameworks weren't invented without good reasons after all... 

The interactive dashboard is made using [dc.js](https://dc-js.github.io/dc.js/) and [crossfilter.js](https://github.com/crossfilter/crossfilter). 
The data is processed in the server with [pandas](https://github.com/pandas-dev/pandas), served to the web client as json objects which are then processed 
by crossfilter.js and transformed to interactive charts by dc.js. 

[Metronic](https://keenthemes.com/metronic/) is the used theme. It is highly customized to become a dark theme. 
The static files are stored and served by an AWS S3 bucket. 
 
### The back end
The server side is written in django, with Postgresql database and Redis as cache store and message broker. 

Some of the libraries used:
- [getstream.io](https://getstream.io/) for activities and notifications management
- [mailgun](https://www.mailgun.com/) for email sending
- [skrill](https://www.skrill.com/) as payment processor
- [Redis Queue](https://python-rq.org/) for the task queue implementation (I know, not Celery)
- [django-comments-xtd](https://github.com/danirus/django-comments-xtd) for comments implementation
- [django-allauth](https://django-allauth.readthedocs.io/en/latest/installation.html) for user authentication
- [numpy](https://numpy.org/) and [pandas](https://github.com/pandas-dev/pandas) for vectorizing some heavy calculations on the server

The sports data is retrieved from [sportmonks](https://www.sportmonks.com/) but its important to note that zakanda 
supports more than one data sources. There is a mapping functionality that matches objects between the 
different data sources. 

## Source Code
The code was written in a span of two years and as I was fairly 
inexperienced with web development when I started, some parts that haven't been refactored since, reflect that initial 
inexperience. A typical bad code example is the part that collects the upcoming events, triggered by the "Pick Bets" page. 
What a [mesh](https://github.com/dimyG/zakanda_public/blob/a311f3070fa02b1e8a231ddddd7e8e43c924e464/games/views.py#L313). 
The data needed by the django template, is collected in a number of complex dictionaries in a long chain of 
function calls. I always wanted to throw this part away and completely rewrite it, adding additional functionality like 
search, but other things had priority at the time and eventually this mesh remained. The more recent parts are 
clearly better, for example the data source mapping and data validation [code](https://github.com/dimyG/zakanda_public/blob/master/data_sources/pre_models.py) 
or the Bet Groups and Subscription [code](https://github.com/dimyG/zakanda_public/blob/master/bet_tagging/models.py).