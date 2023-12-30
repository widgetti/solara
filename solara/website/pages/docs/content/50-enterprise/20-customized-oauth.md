# Customize Oauth with fastAPI

If you're using FastAPI integration with solara, the Oauth can be customized if the two supported methods([Auth0](https://auth0.com/) and [Fief](https://fief.dev/)) doesn't fit for you.

## How to configure customized authorization method:

### Implement your own authentication python module that include a `authentication` method like below:

example of: my_own_oauth_authentication.py
```
def authenticate(request: Request):
    """
    :param request: FastAPI request object which is available on every endpoint
    :return: True or False, if False, it will auto matically raise a 401 Unauthorized Exception.
    """
    if token := requests.headers.get('Authorization'):
        return verify_token(token)
```

### Export the path of the module to environment variable

`export AUTH_MODULE_PATH=file/to/your/my_own_oauth_authentication.py`
