GitHub Actions EC2 Blue/Green Deployment
========================================

Cookiecutter Django with GitHub Actions CD (on push to main/master and manual deployment
using a button) to EC2 using CodeDeploy Blue/Green deployment method.

This tutorial covers a lot from the ground up, including: setting up our web server for
automatic deployment on push to main/master, maintaining good security practices from
short explanations, baby steps on which values you should input, setting up a buffering
reverse proxy called NGINX (sync framework only, which will be explained later), setting
up a database using AWS RDS, and a neat FAQ from 0-years of experience in DevOps
explaining how to run Celery alongside your app in either the same server or different
servers.

.. image:: https://img.shields.io/badge/built%20with-Cookiecutter%20Django-ff69b4.svg?logo=cookiecutter
     :target: https://github.com/pydanny/cookiecutter-django/
     :alt: Built with Cookiecutter Django
.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
     :target: https://github.com/ambv/black
     :alt: Black code style

:License: Apache Software License 2.0

Introduction
------------

We'll be deploying a Django application from GitHub Actions on main branch push or
manual button push using the Blue/Green deployment method (no downtime) using
CodeDeploy, EC2 (not ECS; visit my other `tutorial for ECS`_), Parameter Store
(for environment variables), ALB/ELB (AWS load balancers that'll manager your SSL and
for easier configuration IP address configuration for A records) and AWS RDS PostgreSQL.
Blue/Green deployment guarantees no downtime with a catch; you'll need to code with
no-downtime in mind meaning your new database schema/migration or new views/endpoints
shouldn't crash servers that haven't received the new code yet. Visit
`GitLab's database migration docs`_ for a nice guide (GitLab uses Ruby on Rails, but
the concepts are the same for the Ruby + Python ecosystem).

.. _tutorial for ECS: https://github.com/Andrew-Chen-Wang/cookiecutter-django-ecs-github
.. _GitLab's database migration docs: https://docs.gitlab.com/ee/development/migration_style_guide.html#avoiding-downtime

This uses a Django application for deployment; if you're using some other framework
like Ruby on Rails or Flask, I will mention where you can change the code to adjust
to your own. I will be using t2/t3.micro over the course of this tutorial. To properly
estimate your billing, visit `https://calculator.aws/ <https://calculator.aws/>`_

Why did I write this tutorial? Like the ECS tutorial, I was just afraid I forgot all
the concepts. Plus, it's really useful when you have a new project and need to speedrun
getting the application up. The ECS version takes at most 30 minutes (proficiently 15).
This one should take about 20-40 minutes, but first-time readers will take 1-2 hours.

To me, this is a preferable method over my `ECS (containerized/Docker) tutorial`_ which
forces you to save your Docker images somewhere, costing you some extra bucks. Besides
that, both methods are pretty neat.

.. _ECS (containerized/Docker) tutorial: https://github.com/Andrew-Chen-Wang/cookiecutter-django-ecs-github

I prefer to use AWS via the console for two reasons:

1. I am too lazy to learn how to use AWS Cloudformation or Terraform, and I don't
   believe in copying code that I can't eventually understand (i.e. I don't think I'll
   ever be learning the aforementioned code-based services, ansible, etc.)
2. AWS updates their dashboard often, so going to their dashboard often is a good way
   of keeping up with updates. Also knowing your options and the descriptions provided
   is enough for me to be a keeper for the AWS Console.
3. Going through the console offers an opportunity to learn how the entire AWS
   infrastructure works and is nice in comparison to code-based deployment which can
   screw everything up all at once.

What we'll be setting up
^^^^^^^^^^^^^^^^^^^^^^^^

I'll assume you have a production ready setup (cookiecutter-django provides
production.py which will configure your application properties properly) on GitHub.
I'll also assume you have some kind of domain to use and registered in AWS Route 53
with a Hosted Zone (where you'll be charged 50 cents per month just to keep DNS records.
I know... and I don't know why...).

Explanation (you can skip this and head to the `Deployment <#Deployment>`_ section):

We'll be adding a buffering reverse proxy called Nginx. You can think of it as another
load balancer; if you've ever used Sentry and not have a buffer proxy (not the same as
a WSGI/ASGI server like gunicorn/uwsgi), you'll know that a bunch of bots keep
attacking an IP address of one of your servers instead of through your ALB/ELB (i.e.
external load balancer). That's where your server may crash if you didn't have a
certificate configured with it.

We'll also be adding an HTTP server that is production suitable. The default local
server your web framework provides does not give many options that a dedicated server
can give such as threading, different methods of distributing HTTP requests (i.e. worker
types like Uvicorn workers + Gunicorn for ASGI/PubSub type work), how much resources to
the server should be allowed to consume like cores and memory, etc.. You may be
wondering why your framework doesn't offer these things.

Your web framework is dedicated to being a web framework, not a server. Through the
open source philosophy, we've packaged our things into small-ish modules that have
their own dedicated work. Hence, you'll see Django, Flask, and Rails application say
to use Gunicorn/Unicorn all the time regardless of the web framework in use.

Deployment
----------

Pre-requisites:

* You are logged in to AWS Console
* Have a domain, preferably in Route 53. If you just registered a domain from a
  different registrar like Google Domains, you need to wait 60 days before being able
  to transfer as required by ICANN. It's manageable not being on AWS Route 53, but will
  take more steps that I'm not going to bother explaining. (i.e. I made that stupid
  mistake of using Google Domains knowing I'd be running on AWS lmao). I'll explain
  what you can try to do in those sections.

GitHub Integration
^^^^^^^^^^^^^^^^^^

1. Head to the AWS Console
2. Search for CodeDeploy. Go to the Applications tab.
3. Create an application. The name can be anything like your project name. Compute
   platform should be "EC2/On-premises"
4. You may end up in Applications/application tab. If so, go back to the Applications
   tab to see all your Applications listed.
5. Copy your Application name. Head to your repository on GitHub. Go to settings. In
   the Secrets tab, add a repository secret. The name should be
   ``AWS_CODEDEPLOY_APPLICATION_NAME``, and the value should be your CodeDeploy
   application name.
6. Go back to AWS CodeDeploy dashboard. Select your application and press "Deploy
   application." Don't worry! This will not create a deployment! Just press it and
   relax :)
7. You should now be in the Deployment settings. Find Revision type and select the one
   about GitHub (e.g. "My application is stored in GitHub").
8. In the search box that appears, type in your GitHub username / organization name
   just to quickly check if you've made a connection before. If nothing appears, then
   press Connect to GitHub and grant OAuth access to the necessary organizations. If
   you stop using this method, you can head to your personal / organization settings and
   revoke access (`if you need to revoke, follow this`_).
9. After confirming the request for authorization, you'll be back in the menu. Press
   Cancel. Yes, cancel the deployment and discard (it's a button in the confirmation
   modal).

.. _if you need to revoke, follow this: https://docs.aws.amazon.com/codedeploy/latest/userguide/integrations-partners-github.html#behaviors-authentication

Setting up credentials
^^^^^^^^^^^^^^^^^^^^^^

AWS uses roles and IAM users. Users can run certain programs like the AWS CLI and roles
are attached to users and can also be used for selecting how AWS interprets
authorization level for specific functionalities like CodeDeploy which AWS manages --
thus not requiring an IAM user -- but for security sake you can attach a role saying the
manager only has certain permissions.

1. In the AWS Console, search for IAM.
2. Create a User Group. The name can just be your "project-name-Deployment".
3. Scroll to the permissions section and filter by "CodeDeploy" in the search field.
   Make sure to press enter. Check mark the role called ``AWSCodeDeployRole``. If it's
   not there, view Note 1 at the
   `additional notes section at the bottom <#additional-notes>`_.
4. Select Users or find a button saying Create User (DO NOT create a User Group)
5. Give it a username like "project-name-CodeDeploy" and give it Programmatic Access.
   Press next.
6. In the Permission tab, select your user group in the table below. Press next until
   you create the user (you can add tags if you want). Before closing, copy the access
   key ID and the secret access key. Store it somewhere temporarily (like in a txt
   file). If you end up forgetting which type of key is one of them, access key IDs
   typically are shorter and usually start with AKI.
7. Go to your GitHub repository. Go to the Settings. Go to the Secrets tab. Add a
   repository secret with name ``AWS_ACCESS_KEY_ID``, and the value is your access key
   id. Create another secret called ``AWS_SECRET_ACCESS_KEY``, and the value is your
   secret access key. Finally, create another secret called ``AWS_CODEDEPLOY_REGION``,
   and write your CodeDeploy/your account's region. You can find it at the top right.
   If it says ``global``, go to CodeDeploy again and check again. Note: you will never
   see these values again at both GitHub and AWS.
8. Back in the IAM dashboard, go to the Roles tab. Then press Create role.
9. There should be a bunch of services. Since we're using bare EC2 instances, find the
   service CodeDeploy and select it. At the bottom, select "CodeDeploy" (DO NOT select
   ECS or lambda). Then keep going until you need to name your role. I would call it
   "project-CodeDeploy". Then press Create role.

To specify which region this role is allowed to access/manage CodeDeploy, follow this
guide: https://docs.aws.amazon.com/codedeploy/latest/userguide/getting-started-create-service-role.html#getting-started-create-service-role-console

Setting up a VPC
^^^^^^^^^^^^^^^^

If you have different companies, I suggest you make different AWS accounts. You'll still
want to follow the following steps. A VPC here will help us split our code
bases/websites under a single AWS account. In other words, every server-based website
you host should probably have its own VPC. More details about why this is can be found
in the next section about security groups.

1. From the search bar, head to VPC and select "Your VPCs".
2. Name tag can be "project-vpc-01". IPv4 CIDR block should be ``10.0.0.0/16`` (I'm
   using the VPC wizard to check my values). Create the VPC.
3. Head to Subnets and press "Create subnet." Select the VPC you just made. I'm going
   to create 3 subnets since I'm using us-east-2. (if you're in us-east-1, you can
   create 6, one for each availability zone). For each subnet, name it
   ``us-east-2-subnet-a`` where us-east-2 is my region and "a" represents the
   availability zone. The IPv4 CIDR block should be using the ``10.0.0.0/24`` block.
   For the second one, use "-b" and a different block: ``10.0.1.0/24``. Continue this
   pattern until there are no more subnets.

   You can read about creating subnets here: https://docs.aws.amazon.com/vpc/latest/userguide/working-with-vpcs.html#AddaSubnet
   You can read more about the CIDR blocks here: https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Subnets.html#vpc-sizing-ipv4

4. Once you've created your subnet, go to the Internet Gateway tab and press Create
   internet gateway. The name can just be your project's name. Press Create.
5. There should be a banner at the top saying "Attach to a VPC". If not, go to your
   internet gateway. On the top right, there should be a button saying "Action." Press
   that then press "Attach to VPC" and attach it to your custom VPC.
6. Go to the Route Tables tab and create one. The name
   can be "project-route-table-01". Select your custom VPC then press create.
7. You should be in the details for the route table; if so, scroll down to see Routes
   and press "Edit Routes". If not, select your route table and edit its routes.
8. Press "Add route" with destination ``0.0.0.0/0`` and the target is Internet Gateway.
   You might see a popup for your internet gateway; if so, select it and press Save
   Changes.

   * If you didn't see your Internet Gateway, cancel this edit. Head to the Internet
     Gateway tab. Get the Internet Gateway's ID (not the name). It should look like
     igw-etc. Then repeat this step and this time manually fill out the target. If
     there's an error, that means either your internet gateway or your route table
     is not associated with the right VPC.

9. Head to the Subnet association tab and let's edit that. Check all your subnets
   and press "Save associations".

Setting up ACM for HTTPS certificates and EC2 Target Groups
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The following assumes your domain is in Route 53. This is the first time you will
start getting charged. Every month, Route 53 Hosted Zones will start charging 50
cents and your Load Balancer will start charging quite a bit. Maybe $12 per month?

1. Search up ACM, a free service that gets you SSL certificates and renews them like
   Let's Encrypt. Press Get started under "Provision certificates." If you're on a
   dashboard-like screen, just press "Request a certificate."
2. Press "Request a public certificate." Add your domain name and its "www." form as
   well (i.e. write: www.example.com). For the second one press, "Add another name to
   this certificate." Press next; select DNS validation. BUT WAIT! Don't click next
   too fast. When we get to Step 5/Validation, you'll have to add CNAME records.
3. Select each domain by hitting the arrow button and add those CNAME records to your
   DNS. If you're using Route 53, just press the button saying to add it. If you're
   using Route 53 but the button's not there, make sure you have a hosted zone for your
   domain. A hosted zone in Route 53 allows you to customize the DNS records for your
   domain. Finally, press continue. (When you're back on the ACM dashboard You don't
   need for the validation to happen; it'll take time. Just go to the next step)
4. Search up EC2 and head to the Target Groups tab. Then press Create a target group.
5. Target type is Instances since we're only working with EC2 instances. The name can
   be "project-01". This time, that "01" is important. The protocol should be HTTP
   and port 80 since we let our ALB/ELB/Load Balancer handle HTTPS. Select your VPC and
   use protocol version HTTP1 (again since we let ALB handle HTTPS). The default health
   check of HTTP and path being "/" is good enough. Press next and then press "Create
   target group"

Setting up Security Groups
^^^^^^^^^^^^^^^^^^^^^^^^^^

This is really important. Like so important that when I wrote my ECS tutorial it took
me a full week to figure out why I couldn't connect to my server and why my server
couldn't connect to my AWS RDS database and Redis ElastiCache.

In the next paragraph, I'll explain security groups, and you should DEFINITELY READ IT.
This is super crucial to understand when you're trying to fix bugs and maintain security.

What are security groups? They define how we communicate within AWS infrastructure.
If you've ever worked on servers before, you may know about blocking all ports except
for some specific ones. The exact same thing is happening here with the great addition
of specifying groups of servers that can access an instance/server. So my database can
open port 5432 with a security group attached saying "Only EC2 instances from my custom
VPC that have a security group called XYZ can call to my port here." Note the added
vocab VPC. That's right, each security group can only be used within a single VPC --
which also means all instances you ever create for a single website will be limited to
communication to other instances in the same VPCs.

This not only prevents confusion between different projects, but also makes sure that
unauthorized access from, potentially, a hacked server from a different project cannot
access your servers/databases in other VPCs.

Additionally, we can attach security groups to a single EC2 instance. In this tutorial,
out of many groups we create, we'll be creating a security group but not actually use
it. It'll be for SSHing into an EC2 instance in case you need to view some debugging
information or run ``python manage.py shell`` to access production data.

1. Search up EC2 if you're not already there. Head to the Load Balancer tab from the
   side bar. Press "Security Groups".
2. We need to expose our future Load Balancer (explained next) to the public. Create
   a security group with name "WebAccess" and a description saying "It's for ALB".
   Select your custom VPC. The inbound traffic should consist of 4 rules:

   * Type HTTP, with custom source type on source 0.0.0.0/0
   * Type HTTP, with custom source type on source ::/0
   * Type HTTPS, with custom source type on source 0.0.0.0/0
   * Type HTTPS, with custom source type on source ::/0

   The outbound rules should be left on default, but just in case:

   * Type All traffic, destination type Custom at Source 0.0.0.0/0

3. Create another security group. This is for your actual EC2 instances. Name it
   "project-reverse-proxy". Select your custom VPC. The outbound traffic is the same as
   the first one (the default I believe). The inbound traffic should be 1 rule only:

   * Type All Traffic, with custom source type, and find your first security group
     in the Source (it should say the name of the security group you just created).

4. This step may be optional depending on your use-case. For many Django applications
   we typically use the database; this step covers both the database and cache. Just
   note that AWS RDS and ElastiCache is expensive -- $50/month for RDS + $18 for cache.
   You can also host your own database, and, when you grow large, you can perform an
   extraction of all your data and import it into AWS RDS.

   Create another security group. Name it "project-database" (if you also want to set
   this up for caching, you'll need to create another security group). Select your
   custom VPC. The outbound traffic is the same as the first one (the default I
   believe). The inbound traffic should be 1 rule only, regardless if you're hosting
   your database on EC2 or RDS or ElastiCache:

   * Type PostgreSQL or Redis or whatever database service(s) you're using, with custom
     source type, and find your EC2 security group in the Source (it should say the name
     of the security group you just created in Step 3).

Setting up ACM/ELB (Application/Elastic Load Balancer)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

What is a load balancer? It's kinda what it sounds like; it distributes HTTP requests
across all your target groups and within each group is a server/instance. There are
different styles like Round Robbin, but the ALB is special in that it has an in-house
solution of detecting crashed servers (with health checks).

Note: your Load Balancer will start charging quite a bit. Maybe $12 per month?

1. Search up EC2 if you're not already there. Head to the Load Balancer tab from the
   side bar. Press "Create Load Balancer"
2. Select "Application Load Balancer." Give it a name like "project-alb-01"
   with scheme internet-facing and IP address type ipv4. In listeners, add a listener
   for HTTP with port 80 and HTTPS with port 443. Make sure both are there. Under
   Availability Zones, select your custom VPC and checkmark all your custom subnets.
   Continue. In the next section, choose a certificate from ACM and your certificate
   name should match your domain from the ACM section.
3. In Configure Security Groups, select the one that had the description about ALB.
4. Configure Routing: select the target group you first made. Finally, hit next and
   create your load balancer.

Setting up EC2 Auto Scaling Group
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Autoscaling helps us automatically create or remove servers based on server load. Server
load is based on resource metrics (this is correlated with number of requests). This
helps makes sure requests don't take too long to get a response for due to servers
not having enough resources to effectively run all their requests and generate an HTTP
response.

1. Search up EC2 and head to the Launch Templates tab (from the side bar). Press Create
   Launch Template.
2. The template name can be like "project-MainLaunchTemplate". The description can be
   "Initial production webserver for PROJECT." There may be an option saying
   "Auto Scaling guidance". If you want, you can checkmark it; I did :)
3. Select an AMI; I HIGHLY recommend you choose an Ubuntu LTS (the latest LTS)
4. Your instance type is up to you. For this tutorial, I'm using ``t2.micro`` which has
   1 GiB Memory and 1 core. I highly recommend something a little better (obviously you
   can create a new Launch Template. Don't worry. Everything can be changed!). For Key
   Pair, give a decent key pair name like "project-ec2-keypair". Choose ``.pem`` if
   you're on a Mac/Linux/WSL and ``.ppk`` if you're on Windows. The default volume of
   8 GiB is enough. For Purchasing option, DO NOT checkmark Request Spot Instances
   since it's configurable in your autoscaling group. If you're curious what pricing
   spot instances are, head to EC2/Spot Requests and find Pricing History at the top.
   Finally, Press "Create launch template."
5. Search up EC2 and head to the Auto Scaling Groups tab (from the side bar menu at the
   very bottom). Press Create Auto Scaling Group.
6. The name can be something like "project-EC2AutoScalingGroup". Select the Launch
   Template you just made. Use the default version and just press Next.
7. Instance purchase options should have an option saying "Combine purchase options and
   instance types" so that you can use both On-Demand and Spot instances. For us, we're
   going to have 0 On-Demand instances. "Spot allocation strategy per Availability Zone"
   should use lowest price with a pool of 2. `Click here to learn more about the pool`_.
   Give 100% to our Spot instances. Enable Capacity rebalance so that we have true
   Blue/Green (if you used On Demand only, then this wouldn't be necessary. Because
   we're using Spot instances, an instance could be taken down and another could never
   come back up if we don't bid for another instance. In that case, this option lets us
   wait the deployment out until we can get a new instance.).
8. Keep the default instance types. Choose your custom VPC and select all subnets.
   Click next. Choose existing load balancer. Select Choose from your load balancer
   target group. Make sure to select your target group. Click next. Our group size
   should always be 1. Don't enable Scaling policies. You can set it up later. Don't
   enable scale-in protection. It basically means that, based on metrics/current
   resource consumption, if it drops lower, then don't bring down instances. I think
   having dynamic scale-in, scale-out policy is better to conserve costs though.
   Finally, create your Autoscaling Group.

.. _Click here to learn more about the pool: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-fleet-configuration-strategies.html#plan-ec2-fleet

Setting up the Database (AWS RDS)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you don't need a database then you can skip this portion. I will not be covering a
cache setup, but the concepts here remain the same: VPC, security group attachment,
and checking your costs.

This is the most expensive piece: the database. I'm going to use the cheapest option,
a t2.micro instance, costing my $26 per month. Check your metrics everyday to see if you
need to upgrade your instance, and, yes, it's configurable/updatable. Don't worry.

1. Search up RDS. Go to the Databases tab and press Create database.
2. Choose Standard create. I'm selecting PostgreSQL to match with my security group and
   needs. I always prefer the latest database version since database services are very
   good with backwards compatibility. Use the Production template. Call the database
   instance "project-database-01" (in case you need to set up read replicas later on).
3. You should create a random username and password. I highly recommend you run this
   script to do so (there is also an option to let AWS generate a password. If you
   select that option instead, then, after you create the database, the password will
   appear in a banner or modal):

.. code-block:: python

    import string, random

    def generate_random_string(
        length, using_digits=False, using_ascii_letters=False, using_punctuation=False
    ):
        """
        Example:
            opting out for 50 symbol-long, [a-z][A-Z][0-9] string
            would yield log_2((26+26+50)^50) ~= 334 bit strength.
        """
        symbols = []
        if using_digits:
            symbols += string.digits
        if using_ascii_letters:
            symbols += string.ascii_letters
        if using_punctuation:
            all_punctuation = set(string.punctuation)
            # These symbols can cause issues in environment variables
            unsuitable = {"'", '"', "\\", "$"}
            suitable = all_punctuation.difference(unsuitable)
            symbols += "".join(suitable)
        return "".join([random.choice(symbols) for _ in range(length)])

    print("username", generate_random_string(32, using_ascii_letter=True))
    print(
        "password",
        generate_random_string(64, using_digits=True, using_ascii_letters=True)
    )

4. My db instance class was a Burstable db.t3.micro costing me $13 per month, excluding
   monthly storage costs (which is cheaper if you constantly increment your storage by
   monitoring storage consumption). If you need help with calculating prices, visit
   `calculator.aws <https://calculator.aws/>`_. For my Storage type, I chose General
   Purpose (SSD) with an allocated storage of 20 GiB, the minimum, costing me $4.60.
   Enable storage autoscaling. To prevent spam attacks from ruining my bill, I've made
   the maximum storage threshold be 100 GiB. I chose not to use a Multi-AZ deployment
   approach, and instead if my database goes down then it goes down... The Multi-AZ
   approach creates a backup database in a different region in case master goes down.
5. Choose your custom VPC. Let AWS create a new DB Subnet Group. No public access.
   Then choose your security group for the database. Enable Password authentication
   only.
6. Open the Additional configuration dropdown. You need to name your database. You can
   run the above Python script again like so:
   ``print(generate_random_string(64, using_digits=True, using_ascii_letter=True))``
7. Enable automated backups. The backup window should be at a specific time when the
   least number of users are predicted to be online. Make sure to enable auto minor
   version upgrade. Also be sure to select a maintenance window (something AWS would
   randomly perform otherwise). Leave the rest of the defaults alone and press Create.

Make sure you did not delete those generated values. We still need to store everything
inside Parameter Store, our environment variable / secrets manager.

For restoring your backups, visit the docs: https://docs.aws.amazon.com/aws-backup/latest/devguide/restoring-rds.html

Setting up our CI/CD using GitHub Actions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

TL;DR copy and paste the `CI File`_ at `.github/workflows/ci.yml`_ if you're using
Django. If you're using a different framework, look in the file and change the portions
I tell you in the comments inside the huge dashed line sections to change.

Next, we need to set up the actual deployment pipeline. In our small scale, we're going
to push to our production servers on push to main/master branch. For some larger
organizations, you can instead create a deployment via GitHub releases. Either work.

The current CI/CD configuration is tailored to Django applications and is in
`.github/workflows/ci.yml`_. Copy and paste it in your
repository and in the exact same path (as required by GitHub actions). There are
comments in the file surrounded by huge dashed lines that'll direct you to which
portions to change. For the most part, the AWS portion should remain untouched.

.. _CI File: ./.github/workflows/ci.yml
.. _.github/workflows/ci.yml: ./.github/workflows/ci.yml

The way the workflow works is that every time you push a new commit, we run the CI. If
the tests pass (specifically pytest for testing our application and our linter using
pre-commit which I recommend for everyone regardless of the lang you're using), then we
immediately run our deployment workflow. This workflow file also runs for pull requests,
but deployments are not run.

Note that you can also use GitLab with their CI. Just know that the steps for GitHub
integrations won't be necessary; you'll instead need to choose S3 and your CI file will
need to specify an S3 bucket. That S3 bucket then needs to store your project files.

Adding our environment variables
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

We now need to add our environment variables for use on our servers.

1. Search for Systems Manager. Go to the Parameter Store tab.
2. Double check that you are in the correct region.
3. For each environment variable you need, press Create parameter. I **highly highly**
   recommend that all your parameter names have a prefix like ``PROJECT/SECRET`` where
   "SECRET" is the actual name you want the environment variable to be. This allows for
   easier identification of parameters between projects hosted on the same AWS account.
   Use Standard tier and text data type and paste your environment variables.
4. That prefix is extremely important in all your secret values. In `start_server`_,
   change that prefix value to yours. In my Python application, I'm using
   ``os.environ["DATABASE_URL"]`` but my parameter store key is called
   ``PREFIX/DATABASE_URL``. This is because I grabbed all the parameters via the path
   prefix (i.e. the ``PROJECT/``) and stored it as a JSON in the path ``/.env.json``.
   For cookiecutter-django/django-environ users, I've created a class ``Env`` which
   takes that JSON file and inserts the key/values into ``os.environ``.

If you'd like, in your `start_server`_ file, you can specify a region where you created
your parameters by appending ``--region us-east-2``.

Setting up Scripts to setup our Servers
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In our Launch Template step, we wanted Ubuntu servers. Here, we're going to install our
(i.e. my) preferred Python version, installing our necessary packages, and finally
running the server.

1. Copy `appspec.yml <./appspec.yml>`_. There are comments inside explaining what's
   going on. In a nutshell, this is how CodeDeploy knows 1. where to store our project
   files on the server and 2. where and what scripts to run using specific hooks which
   have a unique lifecycle (e.g. ApplicationStop will trigger ApplicationStart but skips
   BeforeInstall).
2. Copy the `scripts <./scripts>`_ directory. In `install_dependencies`_, you can see me
   updating and upgrading Ubuntu packages, setting up my preferred Python version,
   collecting staticfiles, and installing my Python packages. Adjust to your needs.
   `start_server`_ is preparing the actual start command for my server (for Django,
   it's gunicorn). If you choose to delete the ``stop_server`` script, then make sure
   to update ``appspec.yml``.
3. In `start_server`_, we're grabbing all our environment variables from Parameter
   Store and injecting it into our local environment. Adjust to your needs.

You may also notice us installing NGINX in the `install_dependencies`_ script. NGINX is
our buffering reverse proxy. Please read the comments in the script file. Note: it is
only necessary if you're using a sync server (i.e. if you're using Ruby and you're not
doing long polling, websockets, or comet, or if you're on Django or Flask and you're
using gunicorn and not uvicorn i.e. not using ASGI or any async def/coroutine stuff).

.. _install_dependencies: ./scripts/install_dependencies
.. _start_server: ./scripts/start_server

Finalizing Per-Deployment Script
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

We're going to take advantage of GitHub Actions one more time. For many frameworks, we
have a form of migrations like Django migrations, Alembic, etc. for a new database
schema. But we don't want all our instances running it. In that case, Django and Flask
provide a great utility for calling manage.py commands without the CLI. For Django,
it's ``call_command`` and Flask should use Alembic itself. I can't disclose how I did it
for my previous employer for Flask, but the solution is actually quite simple to create.

1. In this repo, visit `my_awesome_project/users/views.py`_ and take a look at the
   ``migrate`` function. In Django and Flask terminology, this is a "view" or an
   endpoint. In this view, we check the headers for an Authorization token. The settings
   for this authorization token is not set, but, so long as you read my tutorial for the
   environment variable section, it shouldn't be a problem to add to Parameter Store.
   Once authorized, we run the migrate command and send a JSON response specifying the
   latest migration name/revision ID on our production database.
2. Additionally, visit `my_awesome_project/users/management/commands/deployment.py`_.
   There, you see me running an entire deployment script. It migrates our database
   on to the CI database (this is a Django only thing). Then, we can grab the latest
   migration/revision ID. It loops (with 1 second delay) until we receive the right
   data form our endpoint that matches the migration we need.
3. Go back to our GitHub action workflow file and adjust the last run step to your need,
   including what secrets value to use and the Django command to run.

.. _my_awesome_project/users/views.py: ./my_awesome_project/users/views.py
.. _my_awesome_project/users/management/commands/deployment.py: ./my_awesome_project/users/management/commands/deployment.py

Let's Run It!
^^^^^^^^^^^^^

Congrats on getting everything prepared! All that's left to do is to deploy our
application.

You have two options:

1. Go to your GitHub repository. Go to the Actions tab. Press Select Workflow.
   Select ``CI``. Then, press "Run workflow" on your default branch.
2. You can also just commit new changes to your default branch.

Both ways work now and forever in the future!

Credit and License
------------------

Repository is licensed under Apache 2.0; the license file can be found in
`LICENSE <./LICENSE>`_ in the root directory.

Repository created by `Andrew-Chen-Wang`_ sometime in July-August 2021. The original
motive was to set up `donate-anything.org <https://donate-anything.org>`_ (which is
currently defunct as of August 2021). The original idea was to get this working in the
Spring/Summer of 2020, but it got way too complicated and I ended up writing my
`tutorial for ECS`_ instead since that was easier to work with (I mostly got stuck on
Parameter Store and the actual deployment from GitHub Actions. The CodeDeploy app either
just didn't or I just didn't comprehend the concepts of CI/CD, CodeDeploy, etc.; I
didn't understand the concepts very well since I'd only been on GitHub for...
6-ish months? So yea...).

.. _Andrew-Chen-Wang: https://github.com/Andrew-Chen-Wang

Additional Resources
--------------------

FAQ
^^^

**How do I configure Celery and can I configure Celery on the same server?**

Yes; in fact, you have two options for actually running Celery:

* For startups, having a single EC2 instance is cost effective and more easily
  configurable. We have to install something called supervisord. We'll need to set up
  that configuration and run `supervisorctl restart project:*`. Our configuration in
  this case allows us to run both Celery and our Django web app at the same time.

* For those who require multiple servers, having a celery worker per server is overkill
  and a waste of money/resources, I instead advise you to use a new EC2 Autoscaling
  Group. In the CI workflow file, you'll need to edit
  ``--target-instances ${{ secrets.AWS_AUTOSCALING_GROUP_NAME }}`` to have both your web
  app's autoscaling group and your Celery worker autoscaling group.

**Can I run multiple websites like this?**

Yes. I, however, explicitly mentioned why not to (to have separate VPCs per project for
security) and to have different configurations. Also know that it'll be annoying when
one repository commits, all servers go down together. The method of setting this up is
the same as the celery bullet point above.

Links
^^^^^

These are the additional resources that I used to create this tutorial

* Connecting CodeDeploy to GitHub: https://docs.aws.amazon.com/codedeploy/latest/userguide/deployments-create-cli-github.html
  (`archived version of the integration docs <https://web.archive.org/web/20210304165932/https://docs.aws.amazon.com/codedeploy/latest/userguide/deployments-create-cli-github.html>`_)

* Creating the deployment: https://docs.aws.amazon.com/codedeploy/latest/userguide/deployments-create-cli.html
* Creating a subnet: https://docs.aws.amazon.com/vpc/latest/userguide/working-with-vpcs.html#AddaSubnet
* Internet Gateway and Route Table: https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Internet_Gateway.html#Add_IGW_Attach_Gateway
* Appspec "files" section: https://docs.aws.amazon.com/codedeploy/latest/userguide/reference-appspec-file-structure-files.html
* If you're curious what pricing and its price history for spot instances are, head to EC2/Spot Requests and find Pricing History at the top.
* Documentation for pricing for Spot Requests using Autoscaling: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-fleet-configuration-strategies.html
* Creating a CodeDeploy service role: https://docs.aws.amazon.com/codedeploy/latest/userguide/getting-started-create-service-role.html#getting-started-create-service-role-console

Additional Notes
^^^^^^^^^^^^^^^^

1. If you can't find the role, skip creating the User Group. Go back to IAM and go to
   the Users section. Press Create User and select "Attach existing policies directly",
   and finally press Create policy and copy the role below:

.. code-block:: json

    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "autoscaling:CompleteLifecycleAction",
                    "autoscaling:DeleteLifecycleHook",
                    "autoscaling:DescribeAutoScalingGroups",
                    "autoscaling:DescribeLifecycleHooks",
                    "autoscaling:PutLifecycleHook",
                    "autoscaling:RecordLifecycleActionHeartbeat",
                    "autoscaling:CreateAutoScalingGroup",
                    "autoscaling:UpdateAutoScalingGroup",
                    "autoscaling:EnableMetricsCollection",
                    "autoscaling:DescribePolicies",
                    "autoscaling:DescribeScheduledActions",
                    "autoscaling:DescribeNotificationConfigurations",
                    "autoscaling:SuspendProcesses",
                    "autoscaling:ResumeProcesses",
                    "autoscaling:AttachLoadBalancers",
                    "autoscaling:AttachLoadBalancerTargetGroups",
                    "autoscaling:PutScalingPolicy",
                    "autoscaling:PutScheduledUpdateGroupAction",
                    "autoscaling:PutNotificationConfiguration",
                    "autoscaling:PutWarmPool",
                    "autoscaling:DescribeScalingActivities",
                    "autoscaling:DeleteAutoScalingGroup",
                    "ec2:DescribeInstances",
                    "ec2:DescribeInstanceStatus",
                    "ec2:TerminateInstances",
                    "tag:GetResources",
                    "sns:Publish",
                    "cloudwatch:DescribeAlarms",
                    "cloudwatch:PutMetricAlarm",
                    "elasticloadbalancing:DescribeLoadBalancers",
                    "elasticloadbalancing:DescribeInstanceHealth",
                    "elasticloadbalancing:RegisterInstancesWithLoadBalancer",
                    "elasticloadbalancing:DeregisterInstancesFromLoadBalancer",
                    "elasticloadbalancing:DescribeTargetGroups",
                    "elasticloadbalancing:DescribeTargetHealth",
                    "elasticloadbalancing:RegisterTargets",
                    "elasticloadbalancing:DeregisterTargets"
                ],
                "Resource": "*"
            }
        ]
    }
