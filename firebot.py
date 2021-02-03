from twitter import TwitterError
import twitter
import logging
import json
import time

#  Put your keys here
api = twitter.Api(consumer_key='',
                  consumer_secret='',
                  access_token_key='',  # To log into my account
                  access_token_secret='')  # To log into my account

# Set your search terms
terms = [
    "#EndOurCladdingScandal",
    "#VoteForLeaseHolders",
    "#claddingscandal"
]

# How long the script should pause for after doing a like or retweet
SECONDS_BETWEEN_ACTIONS = 15

# Allows set up of multiple loggers. We use this so we can keep debug logs elsewhere
# https://stackoverflow.com/questions/11232230/logging-to-two-files-with-different-settings
def setup_logger(name, log_file, level=logging.INFO):
    handler = logging.FileHandler(log_file)
    handler.setFormatter(formatter)
    new_logger = logging.getLogger(name)
    new_logger.setLevel(level)
    new_logger.addHandler(handler)
    return new_logger

logging.basicConfig(level=logging.INFO)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
logger = setup_logger('MainLogger', 'application.log')
tweet_logger = setup_logger('TweetLogger', 'tweet-debug.log', level=logging.INFO)


class Tweet:
    """ Cut down tweet model for streamed responses """
    def __init__(self, tweet):
        """Constructor method"""
        self.url = f"https://twitter.com/i/web/status/{tweet['id']}"
        self.is_favorited = tweet['favorited']
        self.is_retweeted = tweet['retweeted']
        self.id = tweet['id']

        if 'retweeted_status' in tweet:
            self.type = 'retweet'
        elif tweet['in_reply_to_status_id']:
            self.type = 'reply'
        else:
            self.type = 'status'

        if 'quoted_status' in tweet:
            self.type = 'quote'

    def __str__(self):
        """ Like java toString() """
        # Gets the dictionary representation of the object and turns it into JSON
        return json.dumps(self.__dict__)


retweet_count = 0
favorite_count = 0


def like(tweet):
    global favorite_count
    # Check if I've already liked this before sending to avoid API error
    fav = api.GetStatus(status_id=tweet.id)
    if not fav.favorited:
        logger.info(f"Liking {tweet.url}")
        api.CreateFavorite(status_id=tweet.id)
        favorite_count = favorite_count + 1
        # With a free account you might hit the Twitter rate limit
        # which the client doesn't handle well, so take it easy...
        time.sleep(SECONDS_BETWEEN_ACTIONS)
    else:
        logger.info(f"Status [{tweet.url}] already liked")


def retweet(tweet):
    global retweet_count
    # Check if I've already retweeted this before sending to avoid API error
    rt = api.GetStatus(status_id=tweet.id)
    if not rt.retweeted:
        logger.info(f"Retweeting {tweet.url}")
        api.PostRetweet(status_id=tweet.id)
        retweet_count = retweet_count + 1
        # With a free account you might hit the Twitter rate limit
        # which the client doesn't handle well, so take it easy...
        time.sleep(SECONDS_BETWEEN_ACTIONS)
    else:
        logger.info(f"Status [{tweet.url}] already retweeted")


while (True):
    # Wrap the Tweet Stream in exception handling in case the stream itself fails
    try:
        # Configures the type of data we want to stream from twitter
        # https://developer.twitter.com/en/docs/tweets/filter-realtime/overview
        stream = api.GetStreamFilter(
            # https://developer.twitter.com/en/docs/tweets/filter-realtime/guides/basic-stream-parameters#track
            track=terms,
            languages=['en'],
            filter_level='low')

        for tweet in stream:
            try:
                # tweet_logger.debug(tweet)
                t = Tweet(tweet)
                logger.info(f"Found {t.type} [{t.id}]")

                if not t.is_favorited:
                    like(t)

                if t.type == 'status' and not t.is_retweeted:
                    retweet(t)

            except TwitterError as e:
                if e.message == {'Unknown error': ''}:
                    logger.error(f"Looks like you might have hit your rate limit. Pausing for 15 minutes...")
                    time.sleep(900)
                else:
                    logger.error(f"Something wrong with twitter... {tweet['id']}", e)
            except Exception as e:
                logger.error(f"Something went wrong with Tweet {tweet['id']}", e)

            logger.info(f"Progress: {favorite_count} likes and {retweet_count} retweets")

    except Exception as e:
        logger.error(f"Something went wrong with the twitter stream. Hopefully this will just restart {e}")