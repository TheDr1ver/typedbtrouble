# Internal gRPC call error 8 during concurrent queries

Ref: https://github.com/vaticle/typedb-client-python/issues/261

## **[SOLVED]**

Of course, after taking about a day and a half to put together a nice testing
scenario I was able to find out a solution to my problem (though maybe not the
underlying cause).

Apparently I was just trying to do too much with a single open transaction. Once
I opened a second transaction (and effectively, another client), I had no issues
at all.

A little background as to what caused this in the first place - I'm working on a
web UI for my TypeDB-based tool, and I'm building it with Python Flask. The 
issue would occur when I would launch a web page that took ~14 seconds for the
background searches to fully complete. In the meantime, if someone were to click
a link while the background process was churning, it would throw the `gRPC call
error 8` error.

Fortunately, creating this troubleshooting repo made it easy to test things that 
had the potential to mitigate the error. Once I realized adding a new client
for the second thread caused it to no longer be raised, I tested adding a new
client handler for each Flask route entrypoint and sure enough, that fixed it!

Case closed. Thanks for the public sounding board ;)

## Description

Note this is quite possibly related to [#151](https://github.com/vaticle/typedb-client-python/issues/151), 
but as that issue was closed when grakn was upgraded to TypeDB, I figured this
warranted opening a new issue.

I have a script that does its best to convert all TypeDB Things into individual 
Python objects before handling post-processing functions. I've found that if, 
during that conversion process, the same script is called in a second thread
before the initial script has finished processing, it throws 
`Internal gRPC call error 8`. See below for the initial full traceback that 
caused me to create this repo in the first place.


### Error Message

```
In this particular case, we're trying to generate something akin to the following error:

Traceback (most recent call last):
File "C:\Users\user\.conda\envs\mgmtproj\Lib\site-packages\flask\app.py", line 2091, in __call__
    return self.wsgi_app(environ, start_response)
File "C:\Users\user\.conda\envs\mgmtproj\Lib\site-packages\flask\app.py", line 2076, in wsgi_app
    response = self.handle_exception(e)
File "C:\Users\user\.conda\envs\mgmtproj\Lib\site-packages\flask\app.py", line 2073, in wsgi_app
    response = self.full_dispatch_request()
File "C:\Users\user\.conda\envs\mgmtproj\Lib\site-packages\flask\app.py", line 1518, in full_dispatch_request
    rv = self.handle_user_exception(e)
File "C:\Users\user\.conda\envs\mgmtproj\Lib\site-packages\flask\app.py", line 1516, in full_dispatch_request
    rv = self.dispatch_request()
File "C:\Users\user\.conda\envs\mgmtproj\Lib\site-packages\flask\app.py", line 1502, in dispatch_request
    return self.ensure_sync(self.view_functions[rule.endpoint])(**req.view_args)
File "C:\Users\user\.conda\envs\mgmtproj\Lib\site-packages\flask_login\utils.py", line 272, in decorated_view
    return func(*args, **kwargs)
File "C:\Users\user\OneDrive\Documents\GitHub\MGMT-PROJ\mgmtproj\apps\home\routes.py", line 386, in manage_hunts
    data = dbc.inspect_hunt(
File "C:\Users\user\OneDrive\Documents\GitHub\MGMT-PROJ\mgmtproj\apps\home\db_connector.py", line 688, in inspect_hunt
    res = self.query_db(
File "C:\Users\user\OneDrive\Documents\GitHub\MGMT-PROJ\mgmtproj\apps\home\db_connector.py", line 183, in query_db
    res = self.runner.find_things(
File "C:\Users\user\.hntrproj\plugins\typedb_client\typedb_client.py", line 1464, in find_things
    response_query = self.process_query_answers(
File "C:\Users\user\.hntrproj\plugins\typedb_client\typedb_client.py", line 2101, in process_query_answers
    for answer in answers:
File "C:\Users\user\.conda\envs\mgmtproj\Lib\site-packages\typedb\query\query_manager.py", line 56, in <genexpr>
    return (_ConceptMap.of(cm) for rp in self.stream(query_manager_match_req(query, options.proto())) for cm in rp.match_res_part.answers)
File "C:\Users\user\.conda\envs\mgmtproj\Lib\site-packages\typedb\query\query_manager.py", line 112, in <genexpr>
    return (rp.query_manager_res_part for rp in self._transaction_ext.stream(req))
File "C:\Users\user\.conda\envs\mgmtproj\Lib\site-packages\typedb\stream\response_part_iterator.py", line 77, in __next__
    if not self._has_next():
File "C:\Users\user\.conda\envs\mgmtproj\Lib\site-packages\typedb\stream\response_part_iterator.py", line 72, in _has_next
    return self._fetch_and_check()
File "C:\Users\user\.conda\envs\mgmtproj\Lib\site-packages\typedb\stream\response_part_iterator.py", line 47, in _fetch_and_check
    res_part = self._bidirectional_stream.fetch(self._request_id)
File "C:\Users\user\.conda\envs\mgmtproj\Lib\site-packages\typedb\stream\bidirectional_stream.py", line 80, in fetch
    server_msg = next(self._response_iterator)
File "C:\Users\user\.conda\envs\mgmtproj\Lib\site-packages\grpc\_channel.py", line 426, in __next__
    return self._next()
File "C:\Users\user\.conda\envs\mgmtproj\Lib\site-packages\grpc\_channel.py", line 801, in _next
    operating = self._call.operate(
File "src\python\grpcio\grpc\_cython\_cygrpc/channel.pyx.pxi", line 277, in grpc._cython.cygrpc.IntegratedCall.operate

File "src\python\grpcio\grpc\_cython\_cygrpc/channel.pyx.pxi", line 102, in grpc._cython.cygrpc._operate_from_integrated_call

File "src\python\grpcio\grpc\_cython\_cygrpc/channel.pyx.pxi", line 110, in grpc._cython.cygrpc._operate_from_integrated_call

File "src\python\grpcio\grpc\_cython\_cygrpc/channel.pyx.pxi", line 57, in grpc._cython.cygrpc._raise_call_error_no_metadata

ValueError: Internal gRPC call error 8. Please report to https://github.com/grpc/grpc/issues
```

## Environment

1. Python 3.9.12 (Win 10)
2. client-python v 2.9.0
3. TypeDB 2.10.0
4. TypeDB is running on localhost (Win 10)

## Reproducible Steps

**WARNING** If you have an existing database named `troubleshoot_db`, you should
modify ln 47 because one of the first things this script does is delete that db
to start fresh.

1. Install and run a TypeDB server on localhost:1729
2. Clone this repository and `cd ./grpc_error_8`
3. `python grpc_error_8.py`

The script will create a new database named `troubleshoot_db` and pre-populate it
with random dummy data based on the included schema.

Once the database is populated, the script  will spawn two threads that attempt 
to query the data and perform the transaction operations necessary to convert 
the TypeDB data into its corresponding Python objects (the object frameworks 
are not included or necessary for the purpose of this exercise).

While the initial thread is processing, as soon as the second thread is called 
it will throw the aforementioned error, causing the initial results not to return.

## Expected Output

Process both threads independently without the second thread causing the first
thread to crash.

## Actual Output

`ValueError: Internal gRPC call error 8. Please report to https://github.com/grpc/grpc/issues`

