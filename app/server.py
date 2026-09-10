#!/usr/bin/env python3
"""ADMIN server entrypoint.

The production implementation lives in production.py so the executable entry
point stays stable for local and deployment commands.
"""
from production import *

if __name__ == '__main__':
    init()
    materialize()
    threading.Thread(target=worker, daemon=True).start()
    print(f'ADMIN production server on http://127.0.0.1:{PORT}')
    ThreadingHTTPServer((HOST, PORT), H).serve_forever()
