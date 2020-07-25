#!/usr/bin/env python3.8

from bottle import route, run, hook, request, default_app, TEMPLATE_PATH, template, static_file
from datetime import datetime
import redis
from apscheduler.schedulers.background import BackgroundScheduler

domains_days_dict = dict()

r = redis.Redis()


def is_redis_available():
    try:
        r.ping()
    except Exception as e:
        print("Redis is not available:", str(e))
        return False
    return True


def get_domain_info_from_redis(domain):
    if is_redis_available():
        if (info := r.hget(domain, 'exp')):
            info = info.decode('utf-8')
            updated = datetime.fromtimestamp(
                int(r.hget(domain, 'updated').decode('utf-8'))).strftime('%Y-%m-%d %H:%M:%S')
            if info.isnumeric() or type(info) is int:
                info = round((int(info) - datetime.now().timestamp())/86400)
            domains_days_dict[domain] = (info, updated)


def get_all_from_redis():
    if is_redis_available():
        for key in r.keys('*'):
            get_domain_info_from_redis(key)


def update_outdated_from_redis():
    if is_redis_available():
        for domain in domains_days_dict:
            updated = datetime.strptime(
                domains_days_dict[domain][1], '%Y-%m-%d %H:%M:%S')
            diff = datetime.now() - updated
            if diff.days * 60*60*24 + diff.seconds > 60*60*2:
                get_domain_info_from_redis(domain)


def get_info_from_dict(domains_dict, info_type='all', truncate_errors=0):
    """
    Returns the dict of domain name and tupples with days or errors and last update time.

    Args:
        domains_dict (dict): A dict from domain names (str) and tuple (days/errors, last update time)
        info_type (str): A type of returning info ("days" or "errors")
        truncate_errors(int): do not truncate if 0, truncate to N (positive integer)

    Returns:
        my_dict (dict): The dict with tupples {domain(str): (days(int), last update time)}
        or {domain(str): (error(str), last update time)}
    """
    if info_type == "all":
        my_dict = dict()
        for item in domains_dict:
            if type(domains_dict[item][0]) is str and truncate_errors:
                my_dict[item] = ((domains_dict[item][0])[
                                 0:truncate_errors] + '..', domains_dict[item][1])
            else:
                my_dict[item] = domains_dict[item]
        return my_dict
    if info_type == "days":
        my_dict = dict()
        for item in domains_dict:
            if type(domains_dict[item][0]) is int:
                my_dict[item] = domains_dict[item]
        return my_dict
    elif info_type == "errors":
        my_dict = dict()
        for item in domains_dict:
            if type(domains_dict[item][0]) is str:
                if not truncate_errors:
                    my_dict[item] = domains_dict[item]
                else:
                    my_dict[item] = ((domains_dict[item][0])[
                        0:truncate_errors] + '..', domains_dict[item][1])
        return my_dict


def sort_by_value(domains_dict):
    return {k: v for k, v in sorted(domains_dict.items(), key=lambda item: item[1][0])}


def sort_by_key(domains_dict):
    return dict(sorted(domains_dict.items()))


get_all_from_redis()


TEMPLATE_PATH[:] = ['templates']  # add a directory to template path
DEBUG = 0


@hook('before_request')  # hook to strip the trailing slashes
def strip_path():
    request.environ['PATH_INFO'] = request.environ['PATH_INFO'].rstrip('/')


@route('/static/:path#.+#', name='static')  # for static files like css
def static(path):
    return static_file(path, root='static')


@route('/')
@route('/all')
def show_all():
    if not domains_days_dict and is_redis_available():
        get_all_from_redis()
    return template(
        'all-and-errors',
        domains_good=sort_by_value(get_info_from_dict(
            domains_dict=domains_days_dict, info_type="days", truncate_errors=8)),
        domains_bad=sort_by_key(get_info_from_dict(
            domains_dict=domains_days_dict, info_type="errors", truncate_errors=20)),
        refresh=0)


@route('/hosts')
@route('/domains')
def show_hosts():
    if not domains_days_dict and is_redis_available():
        get_all_from_redis()
    return template(
        'domains',
        domains_days=sort_by_key(get_info_from_dict(
            domains_days_dict, info_type='all', truncate_errors=8)),
        refresh=0)


@route('/errors')
@route('/bad')
def show_hosts():
    if not domains_days_dict and is_redis_available():
        get_all_from_redis()
    return template(
        'domains',
        domains_days=sort_by_key(get_info_from_dict(
            domains_dict=domains_days_dict, info_type="errors", truncate_errors=0)),
        refresh=0)


@route('/days')
@route('/good')
def show_hosts():
    if not domains_days_dict and is_redis_available():
        get_all_from_redis()
    return template(
        'domains',
        domains_days=sort_by_value(get_info_from_dict(
            domains_dict=domains_days_dict, info_type="days", truncate_errors=True)),
        refresh=0)


# TODO: add update outdated from redis

scheduler = BackgroundScheduler()
# TODO: make update only if not info or outdated
job = scheduler.add_job(update_outdated_from_redis, 'interval', seconds=10)
scheduler.start()

# Run bottle internal test server when invoked directly ie: non-uxsgi mode
if __name__ == '__main__':
    run(host='0.0.0.0', port=8080, debug=True, reloader=True)

# Run bottle in application mode.
# Required in order to get the application working with WSGI
else:
    app = application = default_app()
