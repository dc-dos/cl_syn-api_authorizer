# Creating the Client Token for the GlobalWorx API

Making a request to the Globalworx REST API will require setting a properly configured _Client Token_ to be included using
an HTTP Authorization header. This is a multi-step process that provides secured access to the API and ensures that each
request / response transaction only accesses and returns the requesting parties data. This is ensured by first validating the
token and identifying the requestor. The requestor ID is then used to retrieve the requstor profile to verify the requested
endpoint has been authorized for that requestor.

## The TOKEN Process

The TOKEN in the HTTP Authorization header will contain a requestor specific _API_KEY_ that has been encrypted
for safe transversal of the Internet. The API Authorization expects the _API_KEY_ to first be encrypted using the ChaCha20_Poly1305 algorythms and a preset _Cypher_Key_ provided by the GlobalWorx technical staff (it is critical that the requestor treat this value as highly senistive data both in motion and at rest). The encryption process will produce a onetime use _Nonce_ that must be retrieved and appended to the encryption result, delimited by a single colon. This value should then be converted to a Base64 encoded string and then placed in the header. The server authentication process unwinds these layers and retrieves the requestors ID toperform the Authorization.

## ChaCha20_Poly1305

GlobalWorx uses the ChaCha20_Poly1305 based encryption. This algorythm is supported in a large variety of languages,
most often through a 3rd party provided module.  A quick Google search of your target language and _ChaCha20_Poly1305_ will give you a fairly extensive listing. 
