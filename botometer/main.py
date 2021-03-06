from __future__ import print_function
import time
from datetime import datetime

import requests
from requests import ConnectionError, HTTPError, Timeout
import tweepy
from tweepy.error import RateLimitError, TweepError


class NoTimelineError(ValueError):
    def __init__(self, sn, *args, **kwargs):
        msg = "user '%s' has no tweets in timeline" % sn
        super(NoTimelineError, self).__init__(msg, *args, **kwargs)


class Botometer(object):
    _TWITTER_RL_MSG = 'Rate limit exceeded for Twitter API method'

    def __init__(self,
                 consumer_key, consumer_secret,
                 access_token=None, access_token_secret=None,
                 mashape_key=None,
                 start_date=None, end_date=None,
                 **kwargs):
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.access_token_key = self.access_token = access_token
        self.access_token_secret = access_token_secret
        self.wait_on_ratelimit = kwargs.get('wait_on_ratelimit', False)
        self.start_date = start_date
        self.end_date = end_date

        self.mashape_key = mashape_key

        if self.access_token_key is None or self.access_token_secret is None:
            auth = tweepy.AppAuthHandler(
                self.consumer_key, self.consumer_secret)
        else:
            auth = tweepy.OAuthHandler(
                self.consumer_key, self.consumer_secret)
            auth.set_access_token(
                self.access_token_key, self.access_token_secret)

        self.twitter_api = tweepy.API(
            auth,
            parser=tweepy.parsers.JSONParser(),
            wait_on_rate_limit=self.wait_on_ratelimit,
            )

        self.api_url = kwargs.get('botometer_api_url',
                                  'https://osome-botometer.p.mashape.com')
        self.api_version = kwargs.get('botometer_api_version', 2)

    @classmethod
    def create_from(cls, instance, **kwargs):
        my_kwargs = vars(instance)
        my_kwargs.update(kwargs)
        return cls(**my_kwargs)


    def _add_mashape_header(self, kwargs):
        if self.mashape_key:
            kwargs.setdefault('headers', {}).update({
                'X-Mashape-Key': self.mashape_key
            })
        return kwargs

    def _bom_get(self, *args, **kwargs):
        self._add_mashape_header(kwargs)
        return requests.get(*args, **kwargs)

    def _bom_post(self, *args, **kwargs):
        self._add_mashape_header(kwargs)
        return requests.post(*args, **kwargs)

    def _get_twitter_data(self, user, full_user_object=False):
        try:
            user_timeline = self.twitter_api.user_timeline(
                    user,
                    include_rts=True,
                    count=200,
                    )

        except RateLimitError as e:
            e.args = (self._TWITTER_RL_MSG, 'statuses/user_timeline')
            raise e

        tweets = []
        for tweet in user_timeline:
            if datetime.strptime(tweet['created_at'], '%a %b %d %H:%M:%S %z %Y') < self.end_date and datetime.strptime(tweet['created_at'], '%a %b %d %H:%M:%S %z %Y') > self.start_date:
                tweets.append(tweet)

        if tweets:
            user_data = tweets[0]['user']
        else:
            user_data = self.twitter_api.get_user(user)
        screen_name = '@' + user_data['screen_name']

        try:
            search = self.twitter_api.search(screen_name, count=100)
        except RateLimitError as e:
            e.args = (self._TWITTER_RL_MSG, 'search/tweets')
            raise e

        mentions = []
        for mention in search['statuses']:
            if datetime.strptime(mention['created_at'], '%a %b %d %H:%M:%S %z %Y') < self.end_date and datetime.strptime(mention['created_at'], '%a %b %d %H:%M:%S %z %Y') > self.start_date:
                mentions.append(mention)

        payload = {
            'mentions': mentions,
            'timeline': tweets,
            'user': user_data,
        }

        if not full_user_object:
            payload['user'] = {
                'id_str': user_data['id_str'],
                'screen_name': user_data['screen_name'],
            }

        return payload


    ####################
    ## Public methods ##
    ####################

    def bom_api_path(self, method=''):
        return '/'.join([
            self.api_url.rstrip('/'),
            str(self.api_version),
            method,
        ])


    def check_account(self, user, full_user_object=False):
        payload = self._get_twitter_data(user,
                                         full_user_object=full_user_object)
        if not payload['timeline']:
            raise NoTimelineError(payload['user'])

        url = self.bom_api_path('check_account')
        bom_resp = self._bom_post(url, json=payload)
        bom_resp.raise_for_status()
        classification = bom_resp.json()

        return classification


    def check_accounts_in(self, accounts, full_user_object=False,
                          on_error=None, **kwargs):

        sub_instance = self.create_from(self, wait_on_ratelimit=True,
                                        botometer_api_url=self.api_url)
        max_retries = kwargs.get('retries', 3)

        for account in accounts:
            for num_retries in range(max_retries + 1):
                result = None
                try:
                    result = sub_instance.check_account(
                        account, full_user_object=full_user_object)
                except (TweepError, NoTimelineError) as e:
                    err_msg = '{}: {}'.format(
                        type(e).__name__,
                        getattr(e, 'msg', '') or getattr(e, 'reason', ''),
                        )
                    result = {'error': err_msg}
                except (ConnectionError, HTTPError, Timeout) as e:
                    if num_retries >= max_retries:
                        raise
                    else:
                        time.sleep(2 ** num_retries)
                except Exception as e:
                    if num_retries >= max_retries:
                        if on_error:
                            on_error(account, e)
                        else:
                            raise

                if result is not None:
                    yield account, result
                    break



start_date = datetime.strptime('Thu May 05 17:04:41 +0000 2016', '%a %b %d %H:%M:%S %z %Y')
end_date = datetime.strptime('Thu May 20 17:04:41 +0000 2016', '%a %b %d %H:%M:%S %z %Y')

mashape_key = "ILJI7szGPEmshmCRDLNk0SbzYCdyp1GYzPZjsnylLLq46lCHop"
twitter_app_auth = {
    'consumer_key': 'AHQEGXPfCdYybuAOlNr9JGVrI',
    'consumer_secret': 'IJ6MQ2TqbjD5TynvYzKJNplyVQLwax3qIvSwTZG0txN8ni8Q6p',
    'access_token': '1069386305228935168-aRYbGwzT1FgDpythuGziCe8rsrC6Fh',
    'access_token_secret': '89ezGheMRDAyxnEgqc0WnrwYuMCW0tipbSUykl16XAlGw',
  }
bom = Botometer(wait_on_ratelimit=True,
                          mashape_key=mashape_key,
                          start_date=start_date,
                          end_date = end_date,
                          **twitter_app_auth)

# Check a single account by screen name
result = bom.check_account('@clayadavis')

print(result)