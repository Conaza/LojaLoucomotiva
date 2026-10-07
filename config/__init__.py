"""Loucomotiva Django project package.

PyMySQL is a pure-Python MySQL driver. Vercel's build image has no MySQL
client headers, so mysqlclient cannot compile there. PyMySQL 1.2+ reports a
mysqlclient-compatible version and can register itself as MySQLdb, which is
what Django's MySQL backend imports.
"""

import pymysql

pymysql.install_as_MySQLdb()
