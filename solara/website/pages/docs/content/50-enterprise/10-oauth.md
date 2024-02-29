# OAuth: authentication and authorization support

## What is OAuth

OAuth (Open Authorization) is an open standard for token-based authentication and authorization. It enables third-party applications to obtain limited access to a user's resources on another service without exposing their credentials. The user can grant access to their resources on one site to another site without sharing their credentials, providing a secure and efficient way to authenticate users.

You have probably used OAuth without realizing it when signing into various online services and applications. For example, when you use "Sign in with Google" or "Log in with Facebook" to access a third-party website or application, you are using OAuth. By leveraging OAuth, these services allow users to authenticate themselves using their existing Google or Facebook credentials, simplifying the login process and reducing the need for users to remember multiple usernames and passwords. OAuth has become an essential aspect of online identity management and is widely used by companies and developers to provide a seamless and secure authentication experience.

## Installing

To install Solara with OAuth support, make sure you have [Solara Enterprise](/docs/enterprise) install by run the following command:

```bash
$ pip install solara solara-enterprise[auth]
```


## OAuth support in Solara

Solara offers two modes for enabling OAuth: private mode and application controlled mode.

### Private mode

In private mode, Solara pages or any static resources are not accessible without being authenticated. This mode is suitable for web servers that should not be publicly accessible. To enable private mode, set the following environment variable:
```bash
SOLARA_OAUTH_PRIVATE=True
```


### Application controlled mode

In application controlled mode, the application is responsible for checking if a user is authenticated. The application can show a login or logout link and provide user information when the user is logged in. Solara comes preconfigured to run on localhost out of the box, and no additional setup is required to enable OAuth for local development and testing.

Here's an example of how to implement OAuth in application controlled mode:

```solara
import solara
from solara_enterprise import auth

@solara.component
def Page():
    if not auth.user.value:
        solara.Button("Login", icon_name="mdi-login", href=auth.get_login_url())
    else:
        userinfo = auth.user.value['userinfo']
        if 'name' in userinfo:
            solara.Markdown(f"### Welcome {userinfo['name']}")
        solara.Button("Logout", icon_name="mdi-logout", href=auth.get_logout_url())
```
## How to configure OAuth

Solara supports the following OAuth providers: [Auth0](https://auth0.com/) and [Fief](https://fief.dev/).


### Configuring Auth0

By default, Solara is configured with a test Auth0 account. This is useful for testing, but you should not use this in production. This account does limit solara running on localhost, port 8765 to 8770 (and 18765 to 18770 for running the tests).

To configure your own Auth0 provider, you need to change the following environment variables from their defaults:

```bash
# required if you don't use the default test account
SOLARA_SESSION_SECRET_KEY="change me"
# found in the Auth0 dashboard Applications->Applications->Client ID
SOLARA_OAUTH_CLIENT_ID="cW7owP5Q52YHMZAnJwT8FPlH2ZKvvL3U"
# found in the Auth0 dashboard Applications->Applications->Client secret
SOLARA_OAUTH_CLIENT_SECRET="zxITXxoz54OjuSmdn-PluQgAwbeYyoB7ALlnLoodftvAn81usDXW0quchvoNvUYD"
# found in the Auth0 dashboard Applications->Applications->Domain
SOLARA_OAUTH_API_BASE_URL="dev-y02f02f2bpr8skxu785.us.auth0.com"
```

You can optionally set the following environment variables:

```bash
SOLARA_OAUTH_SCOPE = "openid profile email"
```

### Create your own Auth0 Application


To create your own Auth0 application, follow these steps:

1. Go to the [Auth0 dashboard](https://manage.auth0.com/dashboard/) and click on "Applications" on the left side navigation menu.

    ![Auth0 dashboard](https://dxhl76zpt6fap.cloudfront.net/public/docs/enterprise/oauth/goto-applications.webp)

2. Click on "Create Application".

    ![Create Application](https://dxhl76zpt6fap.cloudfront.net/public/docs/enterprise/oauth/click-create-application.webp)

3. Enter a name for your application and select "Regular Web Applications" as the application type. Click on "Create".

    ![Create Application](https://dxhl76zpt6fap.cloudfront.net/public/docs/enterprise/oauth/name-type-create.webp)

4. Click "Skip Integration" to skip the integration step.

5. Click on the "Settings" tabs and enter the following information:

    - Allowed Callback URLs: `http://localhost:8765/_solara/auth/authorize, https://yourdomain.com/_solara/auth/authorize`
    - Allowed Logout URLs: `http://localhost:8765/_solara/auth/logout, https://yourdomain.com/_solara/auth/logout`

    Note that the localhost URLs are only meant for testing. You can remove them once you are ready to deploy your application.
    We recommend setting up a new application for each environment (e.g. development, staging, production).

    ![Callback URLs](https://dxhl76zpt6fap.cloudfront.net/public/docs/enterprise/oauth/callbacks.webp)

6. Configure Solara.

    At the top of the "Settings" tab, you should see your "Domain", "Client ID" and "Client Secret". You will need to set the following environment variables to these values:

    ```bash
    SOLARA_OAUTH_API_BASE_URL="dev-y02f2bpr8skxu785.us.auth0.com"  # replace with your domain
    SOLARA_OAUTH_CLIENT_ID="ELOFERLovc7e7dPwkxO6WFAljtYj9UzJ"  # replace with your client ID
    SOLARA_OAUTH_CLIENT_SECRET="..."  # not shown here, replace with your client secret
    ```

    ![Settings](https://dxhl76zpt6fap.cloudfront.net/public/docs/enterprise/oauth/configuration-values.webp)

    Set your `SOLARA_SESSION_SECRET_KEY` to a random string. See the [Generating a secret key](#generating-a-secret-key) for a convenient way to generate a secret key.

    If you want to test on localhost, you might also want to set `SOLARA_SESSION_HTTPS_ONLY="false"`

    Now you can run the above solara example using your own auth0 provider.


### Configuring Fief

You can also configure Solara to use our Fief test account. To do this, you need to set the following environment variables:

```bash
SOLARA_SESSION_SECRET_KEY="change me"  # required if you don't use the default test account
SOLARA_OAUTH_CLIENT_ID="x2np62qgwp6hnEGTP4JYUE3igdZWhT-AvjpjwwDyKXU"  # found in the Auth0 dashboard Clients->General Tab->Secret
SOLARA_OAUTH_CLIENT_SECRET="XQlByE1pVIz5h2SBN2GYDwT_ziqArHJgLD3KqMlCHjg" # found in the Auth0 dashboard Clients->General Tab->ID
SOLARA_OAUTH_API_BASE_URL="solara-dev.fief.dev"  # found in the Fief dashboard Tenants->Base URL
 # different from Solara's default
SOLARA_OAUTH_LOGOUT_PATH="logout"
```

### Generating a secret key

To generate a secret key, you can use the following code:

```bash
$ python -c "import secrets; print(secrets.token_urlsafe(32))"
ZgrzSLUyft-JvnNMNJ2LgbCFVqcxPOatANAQhMD5EYU
```

*Note: do not copy this key, run this yourself in a terminal.*


## OAuth Component

Solara provides two convenient components for creating a user interface for login and logout:

 1. [Avatar](/api/avatar): This component shows the user's avatar.
 2. [AvatarMenu](/api/avatar_menu): This component shows a menu with the user's avatar and a logout button.

 ## Python version support

Please note that Python 3.6 is not supported for Solara OAuth.


## Possible issues

### Wrong redirection

If the redirection back to solara return to the wrong address, it might be due to solara not choosing the right default for `SOLARA_BASE_URL`. For instance this variable could be set to `SOLARA_BASE_URL=https://solara.dev` for the solara.dev server. If you application runs behind a subpath, e.g. `/myapp`, you might have to set `SOLARA_ROOT_PATH=/myapp`.
