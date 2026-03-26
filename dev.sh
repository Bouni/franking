#!/bin/sh

TOKEN=$(curl -s -X POST -d '{"username": "admin", "password": "az0ftjtMQ0Ip4IMQkEbuqdjn"}' https://invio.bouni.de/api/v1/auth/login | jq -r .token)

curl -s -X GET -H "Authorization: Bearer $TOKEN" "https://invio.bouni.de/api/v1/invoices/d67e7c28-3f3a-4c4a-b7e7-8e0b3f9dfc81" | jq 
