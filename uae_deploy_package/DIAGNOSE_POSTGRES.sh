#!/bin/bash
# Run this FIRST if PostgreSQL connection fails
echo "====== PostgreSQL Diagnostics ======"

echo ""
echo "[ 1 ] .env file:"
cat /home/noagedevadmin/tutorcloud/tutorcloud-global-dashboard/.env 2>/dev/null || echo "  No .env found"

echo ""
echo "[ 2 ] How India connector connects:"
grep -rn "DB_HOST\|DB_PORT\|DATABASE_URL\|psycopg2\|asyncpg\|pg_dsn" \
  /home/noagedevadmin/tutorcloud/tutorcloud-global-dashboard/ \
  --include="*.py" --include="*.env" --include="*.yaml" 2>/dev/null | head -20

echo ""
echo "[ 3 ] Docker containers (especially postgres):"
docker ps 2>/dev/null || echo "  Docker not available"

echo ""
echo "[ 4 ] Port 5432 listeners:"
ss -tlnp 2>/dev/null | grep 5432 || echo "  Nothing on 5432"

echo ""
echo "[ 5 ] PostgreSQL socket locations:"
find /var/run /tmp /run -name ".s.PGSQL.*" 2>/dev/null || echo "  No sockets found"

echo ""
echo "[ 6 ] PostgreSQL process:"
ps aux | grep postgres | grep -v grep || echo "  No postgres process"

echo ""
echo "[ 7 ] India connector file:"
cat /home/noagedevadmin/tutorcloud/tutorcloud-global-dashboard/utils/db_connector.py 2>/dev/null \
  || cat /home/noagedevadmin/tutorcloud/tutorcloud-global-dashboard/utils/connector.py 2>/dev/null \
  || echo "  Connector file not found at expected paths"
