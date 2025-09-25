from django.db import connection, connections

class SqlPrintingMiddleware(object):
    """
    Middleware which prints out a list of all SQL queries done
    for each view that is processed.  This is only useful for debugging.
    """
    def __init__(self, get_response):
        self.get_response = get_response
    def __call__(self, request):
        response = self.get_response(request)
        self.process_response(request, response)
        return response
    def process_response(self, request, response):
        for name in connections.databases.keys():
            conn = connections[name]
            total_time = 0.0
            for query in conn.queries:
                nice_sql = (query['sql'] or '').replace('"', '').replace(',',', ')
                sql = "\033[1;31m[%s]\033[0m %s" % (query['time'], nice_sql)
                total_time = total_time + float(query['time'])
                print(sql)
            replace_tuple = ("  ", len(conn.queries), str(total_time))
            print("%s\033[1;32m[QUERIES: %s TOTAL TIME: %s seconds]\033[0m" % replace_tuple)
