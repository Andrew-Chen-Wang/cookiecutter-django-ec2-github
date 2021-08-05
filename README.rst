My Awesome Project
==================

Cookiecutter Django with GitHub Actions CD (on push to main/master and manual deployment
using a button) to EC2 using CodeDeploy Blue/Green deployment method.

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
to your own.

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

What we'll be setting up
^^^^^^^^^^^^^^^^^^^^^^^^

I'll assume you have a production ready setup (cookiecutter-django provides
production.py which will configure your application properties properly).
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

1. Head to the AWS Console
2. Search for CodeDeploy. Go to the Applications tab.
3. Create an application. The name can be anything like your project name. Compute
   platform should be "EC2/On-premises"
4. You may end up in Applications/application tab. If so, go back to the Applications
   tab to see all your Applications listed.
5. Select your application and press "Deploy application." Don't worry! This will not
   create a deployment! Just press it and relax :)
6. You should now be in the Deployment settings. Find Revision type and select the one
   about GitHub (e.g. "My application is stored in GitHub").
7. In the search box that appears, type in your GitHub username / organization name
   just to quickly check if you've made a connection before. If nothing appears, then
   press Connect to GitHub and grant OAuth access to the necessary organizations. If
   you stop using this method, you can head to your personal / organization settings and
   revoke access (`if you need to revoke, follow this`_).
8. After confirming the request, press Cancel. Yes, cancel the deployment and discard
   (it's a button in the confirmation modal).

.. _if you need to revoke, follow this: https://docs.aws.amazon.com/codedeploy/latest/userguide/integrations-partners-github.html#behaviors-authentication

Credit, License, and Resources
------------------------------

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

Additional Resources that I used to create this tutorial:

* Connecting CodeDeploy to GitHub: https://docs.aws.amazon.com/codedeploy/latest/userguide/deployments-create-cli-github.html

* Creating the deployment: https://docs.aws.amazon.com/codedeploy/latest/userguide/deployments-create-cli.html
  (`archived version of the integration docs <https://web.archive.org/web/20210304165932/https://docs.aws.amazon.com/codedeploy/latest/userguide/deployments-create-cli-github.html>`_)
