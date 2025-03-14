class InvalidBucketPath(Exception):
    pass


class DynamodbItemNotFoundError(Exception):
    pass


class S3ObjectNotFoundError(Exception):
    pass


class CognitoUserNotFoundError(Exception):
    pass


class MaxRetriesExceededError(Exception):
    pass


class RateLimitExceededError(Exception):
    pass
