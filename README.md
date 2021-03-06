# SSL Checker Dashboard

[![Python application](https://github.com/vensder/ssl-checker-dashboard/workflows/Python%20application/badge.svg)](https://github.com/vensder/ssl-checker-dashboard/actions?query=workflow%3A%22Python+application%22)

The SSL Checker Dashboard allows you to overview the expiration days for the SSL certificates of the hosts from the `checker/hosts.lst` file and send notifications to Slack using Incoming Webhook.

This project created for self-education.

The dashboard built using Bottle Python micro web-framework and Docker and consist of the services: dashboard (scalable), Redis, checker and notifier services.

You can run it in Kubernetes (see `./k8s` directory)

![Diagram](./img/diagrams/ssl-checker-diagram.png?raw=true)

![SSL Checker Dashboard](./img/screenshot.png?raw=true)

## How to run locally

```bash
docker-compose build
docker-compose up -d
docker-compose ps
```

Open the link in a browser: <http://localhost:8080/>

## Run load test

```bash
ab -c 100 -n 10000 http://127.0.0.1:8080/all
```

## How to run in Kubernetes

Tested in MicroK8s: <https://microk8s.io/>. How to configure MicroK8s: <https://microk8s.io/docs>.

```bash
sudo microk8s enable dns ingress
```

```bash
kubectl apply -f ./k8s/dashboard.yml
deployment.apps/dashboard created
service/dashboard created
ingress.networking.k8s.io/dashboard created
service/redis created
deployment.apps/redis created
deployment.apps/checker created
```

```bash
kubectl get ingress
NAME      CLASS    HOSTS              ADDRESS     PORTS   AGE
dashboard   <none>   ssl-checks.local   127.0.0.1   80      47s
```

Add `ssl-checks.local` host to `/etc/hosts` file:

```bash
grep ssl-checks /etc/hosts
127.0.0.1 ssl-checks.local
```

Open in browser: <http://ssl-checks.local/>

## How to copy your own hosts list

If you don't want to load default demo list of hosts during the startup, set the parameter in `docker-compose.yml` file to False:

```yaml
IS_FIRST_LOAD_FROM_FILE_ENABLED=False
```

Then run containers and copy your own file inside the `checker` container, and `checker` service will update the hosts info for the new hosts.

If you use docker-compose, just run the `cp` command:

```bash
docker-compose stop -t 0
docker-compose rm -f
docker-compose up -d
docker cp path-to/your_hosts.lst ssl-checker-dashboard_checker_1:/home/app/hosts.lst
```

Or, if you use Kubernetes, copy your file inside the `checker` Pod, for example:

```bash
kubectl cp path-to/your_hosts.lst \
 default/$(kubectl get pods -l app=checker --no-headers=true | cut -d' ' -f1):/home/app/hosts.lst
```

## How to run notifier with your Slack Webhook

To run notifier service you need to pass Slack webhook URL to environment variable `WEBHOOK_URL` inside the container.

To do that using docker-compose, you just need to create a file `.env` with content:

```yaml
WEBHOOK_URL_FROM_SECRET_ENV_FILE=https://hooks.slack.com/services/xxx/yyy/zzz
```

And after the command `docker-compose up notifier` this environment variable will be injected inside the `notifier` container.

To pass that environment variable to k8s Pod create the `slack-webhook` secret from the same `.env` file:

```bash
kubectl create secret generic slack-webhook --from-literal=webhook=$(cat .env | cut -d'=' -f2)
```

And after that run the `notifier` deployment:

```bash
kubectl apply -f ./k8s/notifier.yml
```
