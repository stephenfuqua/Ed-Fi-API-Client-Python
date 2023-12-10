# Ed-Fi-API-Client-Python

## Motivation

The [Ed-Fi ODS/API](https://techdocs.ed-fi.org/display/ODSAPIS3V71) is a REST
API that support interoperability of student data systems. The API definition,
via the [Ed-Fi Data
Standard](https://techdocs.ed-fi.org/display/ETKB/Ed-Fi+Standards), is
extensible: many large-scale or specialized implementations add their own local
use cases that are not supported out of the box by the Ed-Fi Data Standard
(Extensions). Furthermore, the Data Standard receives regular updates; sometimes
these are merely additive, and from time to time there are breaking changes.
These factors make it impossible to create a one-size fits all client
library.

But, not all is lost: the ODS/API exposes its API definition using
[OpenAPI](https://www.openapis.org/), and we can use [Swagger
Codegen](https://swagger.io/tools/swagger-codegen/) to build a client library
based on the target installation's data model / API spec. The basic process of
creating a C# code library (SDK) is described in Ed-Fi documentation at [Using
Code Generation to Create an
SDK](https://techdocs.ed-fi.org/display/ODSAPIS3V71/Using+Code+Generation+to+Create+an+SDK)
(Note: this link is for ODS/API 7.1, but the instructions are essentially the
same for all versions).

But what about Python? Yes, Swagger Codegen supports Python output. But it is
not quite enough - you also need to manage authentication on your own. And,
running Swagger Codgen requires the Java Development Kit (JDK). The notes below
will walk through generating a client library with help from Docker (no local
install of the JDK required) and demonstrate basic usage of a simple
`TokenManager` class for handling authentication.

## Generating an Ed-Fi Client Package

The Swagger Codegen tool is available as a [pre-built Docker
image](https://github.com/swagger-api/swagger-codegen#public-pre-built-docker-images),
at repository `swaggerapi/swagger-codegen-cli`. We will use it to build a
client package for working with Ed-Fi Data Standard v5.0, which is available through
Ed-Fi ODS/API v7.1. The [ODS/API Landing Page](https://api.ed-fi.org/) has links
to the Swagger UI-based "documentation" (UI on top of OpenAPI specification) for
all currently supported versions of the ODS/API. From there, we can find a link
to the [specification
document](https://api.ed-fi.org/v7.1/api/metadata/data/v3/resources/swagger.json).

The example shell commands use PowerShell, and they are easily adaptable to Bash
or another shell. The generated code will be in a new `edfi-client` directory.
Note that this repository's `.gitignore` file excludes this directory from
source control, since the original intent of this repository is to provide
instructions, not a full-blown client. If you fork this repository and want to
create your own package, then you may wish to remove that line from `.gitignore`
so that you can keep your custom client code in your forked repository.

```powerShell
$url = "https://api.ed-fi.org/v7.1/api/metadata/data/v3/resources/swagger.json"
$outputDir = "./edfi-client"
New-Item -Path $outputDir -Type Directory -Force | out-null
$outputDir = (Resolve-Path $outputDir)
docker run --rm -v "$($outputDir):/local" swaggerapi/swagger-codegen-cli generate `
    -i $url -l python -o /local
```

On my machine, this took about a minute to run. Here's what we get as output:

```powerShell
> ls edfi-client

    Directory: C:\source\Ed-Fi-API-Client-Python\edfi-client


Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
d-----        11/27/2023   9:31 PM                .swagger-codegen
d-----        11/27/2023   9:31 PM                docs
d-----        11/27/2023   9:32 PM                out
d-----        11/27/2023   9:31 PM                swagger_client
d-----        11/27/2023   9:31 PM                test
-a----        11/27/2023   9:31 PM            786 .gitignore
-a----        11/27/2023   9:31 PM           1030 .swagger-codegen-ignore
-a----        11/27/2023   9:31 PM            359 .travis.yml
-a----        11/27/2023   9:31 PM           1663 git_push.sh
-a----        11/27/2023   9:31 PM         351139 README.md
-a----        11/27/2023   9:31 PM             96 requirements.txt
-a----        11/27/2023   9:31 PM           1811 setup.py
-a----        11/27/2023   9:31 PM             69 test-requirements.txt
-a----        11/27/2023   9:31 PM            149 tox.ini
```

We have code, we have tests, and even documentation. Here is a usage example from
one of the auto-generated docs:

```python
from __future__ import print_function
import time
import swagger_client
from swagger_client.rest import ApiException
from pprint import pprint

# Configure OAuth2 access token for authorization: oauth2_client_credentials
configuration = swagger_client.Configuration()
configuration.access_token = 'YOUR_ACCESS_TOKEN'

# create an instance of the API class
api_instance = swagger_client.AcademicWeeksApi(swagger_client.ApiClient(configuration))
id = 'id_example' # str | A resource identifier that uniquely identifies the resource.
if_match = 'if_match_example' # str | The ETag header value used to prevent the DELETE from removing a resource modified by another consumer. (optional)

try:
    # Deletes an existing resource using the resource identifier.
    api_instance.delete_academic_week_by_id(id, if_match=if_match)
except ApiException as e:
    print("Exception when calling AcademicWeeksApi->delete_academic_week_by_id: %s\n" % e)
```

## Converting to Poetry

I like to use [Poetry](https://python-poetry.org/) for managing Python packages
instead of Pip, Conda, Tox, etc. Converting the `requirements.txt` file for use
in Poetry is quite easy with this PowerShell command ([hat
tip](https://stackoverflow.com/a/73691994/30384)):

```powerShell
Push-Location edfi-client
poetry init --name edfi-client -l Apache-2.0
@(cat requirements.txt) | %{&poetry add $_.replace(' ','')}
Pop-Location
```

(The default `requirements.txt` file has some unexpected spaces; the `replace`
command above strips those out).

## Missing Token Generation

Note the line above with `access_token = 'YOUR_ACCESS_TOKEN'`. Swagger Codegen
requires you to bring your own token generation routine. We can build one using
portions of the client library itself. The ODS/API supports the OAuth 2.0 client
credentials flow, which generates an bearer-style access token. A basic HTTP
request for authentication looks like this:

```none
POST /v7.1/api/oauth/token HTTP/1.1
Host: api.ed-fi.org
Content-Type: application/x-www-form-urlencoded
Accept: application/json

grant_type=client_credentials&client_id=YOUR CLIENT ID&client_secret=YOUR CLIENT SECRET
```

There are some variations in how these parameters can be passed, but this may be
the most common / universal format, and this is what we will implement here.

Generated tokens are only good for so long; they expire. When a token expires,
it would be nice if we could recognize that and automatically call for a new
one, instead of encountering an error. The generated code does not support token
refresh, and does not have an obvious hook for how to do so. For a very clean
developer experience, the authentication and refresh mechanisms would be built
into the `ApiClient` class created by Swagger Codegen. But be warned: if you
rerun the generator, it will overwrite your customizations.

Someone with deeper Python expertise can probably come up with multiple ways to
approach the refresh problem. This sample code handles token refresh very
crudely, requiring the _user_ of the code to detect the problem and try to
re-authenticate. Perhaps a [Context
Manager](https://realpython.com/python-with-statement/#creating-function-based-context-managers)
implementation would help here.

See [token_manager.py](./token_manager.py) for a basic implementation to support
authentication. After running the Swagger Codegen tool, you may want to copy
this file into the generated directory:

```powershell
Copy-Item -Path token_manager.py -Destination edfi-client/swagger_client -Force
```

## Demonstration

The following snippet demonstrates use the token manager with a simple token
refresh mechanism. Note that this tries to delete an object that does not exist,
therefore you should expect it to raise an exception with a 404 NOT FOUND
message.

```python
from swagger_client.configuration import Configuration
from swagger_client.token_manager import TokenManager
from swagger_client.api import AcademicWeeksApi
from swagger_client.rest import ApiException

BASE_URL = "https://api.ed-fi.org/v7.1/api"

config = Configuration()
config.username = "RvcohKz9zHI4"
config.password = "E1iEFusaNf81xzCxwHfbolkC"
config.host = f"{BASE_URL}/data/v3/"
config.debug = True

tm = TokenManager(f"{BASE_URL}/oauth/token", config)
api_client = tm.create_authenticated_client()

api_instance = AcademicWeeksApi(api_client)

try:
    api_instance.delete_academic_week_by_id("bogus")
except ApiException as ae:
    if ae.status == 401:
        tm.refresh()
        api_instance.delete_academic_week_by_id("bogus")
    else:
        raise
```

## Legal Information

Copyright (c) 2023 Stephen Fuqua and contributors.

Licensed under the [Apache License, Version 2.0](LICENSE) (the "License").

Unless required by applicable law or agreed to in writing, software distributed
under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

See [NOTICES](NOTICES.md) for additional copyright and license notifications.
