import botometer
import datetime

start_date = datetime.datetime(2018, 1, 19, 12, 00, 00)
end_date = datetime.datetime(2018, 1, 19, 13, 00, 00)

mashape_key = "ILJI7szGPEmshmCRDLNk0SbzYCdyp1GYzPZjsnylLLq46lCHop"
twitter_app_auth = {
    'consumer_key': 'AHQEGXPfCdYybuAOlNr9JGVrI',
    'consumer_secret': 'IJ6MQ2TqbjD5TynvYzKJNplyVQLwax3qIvSwTZG0txN8ni8Q6p',
    'access_token': '1069386305228935168-aRYbGwzT1FgDpythuGziCe8rsrC6Fh',
    'access_token_secret': '89ezGheMRDAyxnEgqc0WnrwYuMCW0tipbSUykl16XAlGw',
  }
bom = botometer.Botometer(wait_on_ratelimit=True,
                          mashape_key=mashape_key,
                          start_date=start_date,
                          end_date = end_date,
                          **twitter_app_auth)

# Check a single account by screen name
result = bom.check_account('@clayadavis')

print(result)